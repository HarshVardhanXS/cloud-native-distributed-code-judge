import logging
import json
import base64
import os
import subprocess
import sys
import tempfile
import time

from celery.exceptions import SoftTimeLimitExceeded
from azure_executor import run_submission_in_aci
from celery_app import celery
from database import SessionLocal
from models import Submission, TestCase
from redis_client import invalidate_leaderboard_cache

logger = logging.getLogger(__name__)


def _run_submission_locally(code: str) -> dict[str, object]:
    """
    Fallback executor for environments where Azure CLI/ACI is unavailable.
    This is intentionally minimal and is not a secure sandbox.
    """
    timeout_seconds = int(os.getenv("LOCAL_EXECUTION_TIMEOUT_SECONDS", "8"))
    started_at = time.perf_counter()
    file_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as tmp_file:
            tmp_file.write(code)
            file_path = tmp_file.name

        proc = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        runtime_ms = int((time.perf_counter() - started_at) * 1000)
        status = "accepted" if proc.returncode == 0 else "error"
        return {
            "status": status,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "exit_code": int(proc.returncode),
            "runtime_ms": runtime_ms,
            "timed_out": False,
            "container_state": "local-fallback",
            "detail": "" if status == "accepted" else "Local execution returned non-zero exit code.",
        }
    except subprocess.TimeoutExpired as exc:
        runtime_ms = int((time.perf_counter() - started_at) * 1000)
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        return {
            "status": "error",
            "stdout": stdout,
            "stderr": (stderr + "\nExecution timed out").strip(),
            "exit_code": 124,
            "runtime_ms": runtime_ms,
            "timed_out": True,
            "container_state": "local-fallback",
            "detail": "Local execution timed out.",
        }
    except Exception as exc:
        runtime_ms = int((time.perf_counter() - started_at) * 1000)
        return {
            "status": "error",
            "stdout": "",
            "stderr": "",
            "exit_code": 1,
            "runtime_ms": runtime_ms,
            "timed_out": False,
            "container_state": "local-fallback",
            "detail": f"Local execution failure: {exc}",
        }
    finally:
        if file_path:
            try:
                os.remove(file_path)
            except Exception:
                logger.warning("Failed to remove temporary execution file: %s", file_path)


def _run_submission_with_testcases_locally(
    code: str,
    testcases: list[TestCase],
) -> dict[str, object]:
    """
    Execute user code against stored testcases in a local subprocess.
    Expected contract: user defines a callable named `solution`.
    """
    timeout_seconds = int(os.getenv("LOCAL_EXECUTION_TIMEOUT_SECONDS", "8"))
    started_at = time.perf_counter()

    case_payload = [
        {"input_data": case.input_data, "expected_output": case.expected_output}
        for case in testcases
    ]
    code_b64 = base64.b64encode(code.encode("utf-8")).decode("ascii")
    cases_b64 = base64.b64encode(
        json.dumps(case_payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")

    runner = f"""
import ast
import base64
import json
import sys
import time

def parse_value(raw):
    if raw is None:
        return None
    raw = str(raw).strip()
    if raw == "":
        return ""
    for parser in (json.loads, ast.literal_eval):
        try:
            return parser(raw)
        except Exception:
            pass
    return raw

def normalize(value):
    if isinstance(value, (dict, list, tuple, int, float, bool)) or value is None:
        try:
            return json.dumps(value, sort_keys=True)
        except Exception:
            return str(value).strip()
    return str(value).strip()

code = base64.b64decode("{code_b64}").decode("utf-8")
cases = json.loads(base64.b64decode("{cases_b64}").decode("utf-8"))
ns = {{}}
exec(code, ns, ns)
solution = ns.get("solution")
if not callable(solution):
    raise RuntimeError("Define a callable function named 'solution'.")

passed = 0
total = len(cases)
details = []
started = time.perf_counter()
for idx, case in enumerate(cases, start=1):
    inp = parse_value(case.get("input_data"))
    exp = parse_value(case.get("expected_output"))

    if isinstance(inp, dict):
        out = solution(**inp)
    elif isinstance(inp, (list, tuple)):
        out = solution(*inp)
    else:
        out = solution(inp)

    ok = normalize(out) == normalize(exp)
    if ok:
        passed += 1
    details.append({{"index": idx, "passed": ok, "actual": out, "expected": exp}})

runtime_ms = int((time.perf_counter() - started) * 1000)
status = "accepted" if passed == total else "wrong_answer"
print(json.dumps({{
    "status": status,
    "passed_test_cases": passed,
    "total_test_cases": total,
    "details": details,
    "runtime_ms": runtime_ms
}}, separators=(",", ":")))
""".strip()

    try:
        proc = subprocess.run(
            [sys.executable, "-c", runner],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        runtime_ms = int((time.perf_counter() - started_at) * 1000)
        if proc.returncode != 0:
            return {
                "status": "error",
                "stdout": proc.stdout or "",
                "stderr": proc.stderr or "",
                "exit_code": int(proc.returncode),
                "runtime_ms": runtime_ms,
                "timed_out": False,
                "container_state": "local-testcase-fallback",
                "detail": "Execution failed while running testcase evaluator.",
            }

        payload = json.loads((proc.stdout or "{}").strip() or "{}")
        return {
            "status": payload.get("status", "error"),
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "exit_code": int(proc.returncode),
            "runtime_ms": int(payload.get("runtime_ms", runtime_ms)),
            "timed_out": False,
            "container_state": "local-testcase-fallback",
            "detail": "",
            "passed_test_cases": int(payload.get("passed_test_cases", 0)),
            "total_test_cases": int(payload.get("total_test_cases", len(testcases))),
        }
    except subprocess.TimeoutExpired as exc:
        runtime_ms = int((time.perf_counter() - started_at) * 1000)
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        return {
            "status": "error",
            "stdout": stdout,
            "stderr": (stderr + "\nExecution timed out").strip(),
            "exit_code": 124,
            "runtime_ms": runtime_ms,
            "timed_out": True,
            "container_state": "local-testcase-fallback",
            "detail": "Local testcase execution timed out.",
        }
    except Exception as exc:
        runtime_ms = int((time.perf_counter() - started_at) * 1000)
        return {
            "status": "error",
            "stdout": "",
            "stderr": "",
            "exit_code": 1,
            "runtime_ms": runtime_ms,
            "timed_out": False,
            "container_state": "local-testcase-fallback",
            "detail": f"Local testcase execution failure: {exc}",
        }


@celery.task(bind=True, soft_time_limit=120, time_limit=150)
def execute_submission(self, submission_id: int):
    db = SessionLocal()
    started_at = time.perf_counter()

    try:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            return {"error": "Submission not found", "submission_id": submission_id}

        submission.status = "running"
        db.commit()

        testcases = db.query(TestCase).filter(
            TestCase.problem_id == submission.problem_id
        ).all()

        if testcases:
            execution = _run_submission_with_testcases_locally(submission.code, testcases)
        else:
            try:
                execution = run_submission_in_aci(submission.code, "python")
            except Exception as exc:
                logger.warning(
                    "ACI execution unavailable for submission %s (%s). Falling back to local execution.",
                    submission_id,
                    exc,
                )
                execution = _run_submission_locally(submission.code)

        status = str(execution.get("status", "error"))
        final_status = status if status in {"accepted", "wrong_answer", "error"} else "error"
        error_detail = str(execution.get("detail") or execution.get("stderr") or "")

        runtime_ms = int(execution.get("runtime_ms") or ((time.perf_counter() - started_at) * 1000))
        submission.status = final_status
        submission.runtime_ms = runtime_ms
        submission.result = json.dumps(
            {
                "stdout": execution.get("stdout", ""),
                "stderr": execution.get("stderr", ""),
                "exit_code": execution.get("exit_code"),
                "container_state": execution.get("container_state"),
                "timed_out": bool(execution.get("timed_out", False)),
                "passed_test_cases": execution.get("passed_test_cases"),
                "total_test_cases": execution.get("total_test_cases"),
            }
        )
        db.commit()
        if final_status == "accepted":
            invalidate_leaderboard_cache()
        return {
            "submission_id": submission_id,
            "status": final_status,
            "runtime_ms": runtime_ms,
            "detail": error_detail if final_status == "error" else "",
        }
    except SoftTimeLimitExceeded:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if submission:
            submission.status = "error"
            submission.runtime_ms = int((time.perf_counter() - started_at) * 1000)
            db.commit()
        logger.warning("Submission %s exceeded Celery soft time limit", submission_id)
        return {
            "submission_id": submission_id,
            "status": "error",
            "runtime_ms": int((time.perf_counter() - started_at) * 1000),
            "detail": "Celery soft time limit exceeded",
        }
    except Exception as exc:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if submission:
            submission.status = "error"
            submission.runtime_ms = int((time.perf_counter() - started_at) * 1000)
            db.commit()
        logger.exception("Submission %s failed during task execution", submission_id)
        return {
            "submission_id": submission_id,
            "status": "error",
            "runtime_ms": int((time.perf_counter() - started_at) * 1000),
            "detail": str(exc),
        }
    finally:
        db.close()
