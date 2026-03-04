import base64
import json
import logging
import os
import subprocess
import time
import uuid
from typing import Any

from config import (
    AZURE_EXECUTION_RESOURCE_GROUP,
    AZURE_LOCATION,
    AZURE_SUBSCRIPTION_ID,
)

logger = logging.getLogger(__name__)

RESULT_MARKER = "__CJ_RESULT__="


class AzureExecutionError(RuntimeError):
    """Raised when Azure execution lifecycle fails."""


def get_azure_execution_config() -> dict[str, str]:
    """
    Return required Azure execution settings.
    Raise a clear error if Azure execution env vars are not configured.
    """
    missing = []
    if not AZURE_SUBSCRIPTION_ID:
        missing.append("AZURE_SUBSCRIPTION_ID")
    if not AZURE_EXECUTION_RESOURCE_GROUP:
        missing.append("AZURE_EXECUTION_RESOURCE_GROUP")
    if not AZURE_LOCATION:
        missing.append("AZURE_LOCATION")
    if missing:
        raise AzureExecutionError(
            "Azure execution is not configured. Missing: " + ", ".join(missing)
        )

    return {
        "subscription_id": AZURE_SUBSCRIPTION_ID,
        "resource_group": AZURE_EXECUTION_RESOURCE_GROUP,
        "location": AZURE_LOCATION,
    }


def _get_executor_settings() -> dict[str, Any]:
    image = os.getenv("AZURE_EXECUTION_IMAGE", "").strip()
    if not image:
        raise AzureExecutionError(
            "Missing AZURE_EXECUTION_IMAGE for ACI execution."
        )

    timeout_seconds = int(os.getenv("AZURE_EXECUTION_TIMEOUT_SECONDS", "30"))
    cpu = float(os.getenv("AZURE_EXECUTION_CPU", "0.5"))
    memory_gb = float(os.getenv("AZURE_EXECUTION_MEMORY_GB", "1.0"))
    poll_interval_seconds = float(os.getenv("AZURE_EXECUTION_POLL_INTERVAL_SECONDS", "2"))

    registry_server = os.getenv("AZURE_EXECUTION_REGISTRY_SERVER", "").strip()
    registry_username = os.getenv("AZURE_EXECUTION_REGISTRY_USERNAME", "").strip()
    registry_password = os.getenv("AZURE_EXECUTION_REGISTRY_PASSWORD", "").strip()

    return {
        "image": image,
        "timeout_seconds": timeout_seconds,
        "cpu": cpu,
        "memory_gb": memory_gb,
        "poll_interval_seconds": poll_interval_seconds,
        "registry_server": registry_server,
        "registry_username": registry_username,
        "registry_password": registry_password,
    }


def _run_az(args: list[str], timeout_seconds: int = 30) -> str:
    try:
        completed = subprocess.run(
            ["az", *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise AzureExecutionError("Azure CLI 'az' was not found in PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise AzureExecutionError(f"Azure CLI command timed out: {' '.join(args)}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise AzureExecutionError(
            f"Azure CLI command failed ({' '.join(args)}): {stderr}"
        ) from exc
    return completed.stdout


def _build_bootstrap_script(code: str, timeout_seconds: int) -> str:
    code_b64 = base64.b64encode(code.encode("utf-8")).decode("ascii")
    return f"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time

code_b64 = "{code_b64}"
timeout_seconds = {timeout_seconds}

fd, path = tempfile.mkstemp(prefix="submission_", suffix=".py")
os.close(fd)
with open(path, "wb") as f:
    f.write(base64.b64decode(code_b64))

status = "accepted"
timed_out = False
stdout = ""
stderr = ""
exit_code = 0
started = time.perf_counter()

try:
    proc = subprocess.run(
        [sys.executable, path],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    exit_code = int(proc.returncode)
    if exit_code != 0:
        status = "error"
except subprocess.TimeoutExpired as exc:
    timed_out = True
    status = "error"
    exit_code = 124
    stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
    captured_stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
    stderr = (captured_stderr + "\\nExecution timed out").strip()
except Exception as exc:
    status = "error"
    exit_code = 1
    stderr = f"Executor failure: {{exc}}"
finally:
    runtime_ms = int((time.perf_counter() - started) * 1000)
    try:
        os.remove(path)
    except Exception:
        pass

if stdout:
    print(stdout, end="")
if stderr:
    print(stderr, end="", file=sys.stderr)

payload = {{
    "status": status,
    "stdout": stdout,
    "stderr": stderr,
    "exit_code": exit_code,
    "runtime_ms": runtime_ms,
    "timed_out": timed_out,
}}
print("{RESULT_MARKER}" + json.dumps(payload, separators=(",", ":")))
""".strip()


def _parse_logs(logs: str) -> dict[str, Any]:
    parsed: dict[str, Any] | None = None
    for line in logs.splitlines():
        if line.startswith(RESULT_MARKER):
            raw = line[len(RESULT_MARKER) :]
            parsed = json.loads(raw)

    if parsed is None:
        return {
            "status": "error",
            "stdout": "",
            "stderr": "Execution result marker not found in container logs.",
            "runtime_ms": None,
            "exit_code": None,
            "timed_out": False,
        }
    return parsed


def run_submission_in_aci(code: str, language: str) -> dict[str, Any]:
    """Execute a submission in Azure Container Instances and return structured result."""
    if language.lower() != "python":
        return {
            "status": "error",
            "stdout": "",
            "stderr": f"Unsupported language: {language}",
            "runtime_ms": None,
            "exit_code": None,
            "timed_out": False,
            "detail": "Only python execution is currently supported.",
        }

    config = get_azure_execution_config()
    settings = _get_executor_settings()
    container_name = f"judge-{uuid.uuid4().hex[:12]}"
    overall_started = time.perf_counter()
    container_created = False

    bootstrap_script = _build_bootstrap_script(
        code=code,
        timeout_seconds=settings["timeout_seconds"],
    )
    bootstrap_b64 = base64.b64encode(bootstrap_script.encode("utf-8")).decode("ascii")
    command_line = (
        "python -c \"import base64; exec(base64.b64decode('"
        f"{bootstrap_b64}"
        "').decode('utf-8'))\""
    )

    create_args = [
        "container",
        "create",
        "--subscription",
        config["subscription_id"],
        "--resource-group",
        config["resource_group"],
        "--name",
        container_name,
        "--location",
        config["location"],
        "--image",
        settings["image"],
        "--restart-policy",
        "Never",
        "--cpu",
        str(settings["cpu"]),
        "--memory",
        str(settings["memory_gb"]),
        "--command-line",
        command_line,
        "--output",
        "json",
    ]

    if (
        settings["registry_server"]
        and settings["registry_username"]
        and settings["registry_password"]
    ):
        create_args.extend(
            [
                "--registry-login-server",
                settings["registry_server"],
                "--registry-username",
                settings["registry_username"],
                "--registry-password",
                settings["registry_password"],
            ]
        )

    try:
        _run_az(create_args, timeout_seconds=120)
        container_created = True

        deadline = time.monotonic() + settings["timeout_seconds"] + 60
        current_state = "Unknown"
        while time.monotonic() < deadline:
            raw_show = _run_az(
                [
                    "container",
                    "show",
                    "--subscription",
                    config["subscription_id"],
                    "--resource-group",
                    config["resource_group"],
                    "--name",
                    container_name,
                    "--output",
                    "json",
                ],
                timeout_seconds=20,
            )
            details = json.loads(raw_show)
            current_state = (
                details.get("containers", [{}])[0]
                .get("instanceView", {})
                .get("currentState", {})
                .get("state", "Unknown")
            )
            if current_state in {"Terminated", "Succeeded", "Failed"}:
                break
            time.sleep(settings["poll_interval_seconds"])
        else:
            return {
                "status": "error",
                "stdout": "",
                "stderr": (
                    f"Timed out waiting for ACI container completion "
                    f"(>{settings['timeout_seconds'] + 60}s)."
                ),
                "runtime_ms": int((time.perf_counter() - overall_started) * 1000),
                "exit_code": None,
                "timed_out": True,
                "detail": "ACI orchestration timeout",
            }

        logs = _run_az(
            [
                "container",
                "logs",
                "--subscription",
                config["subscription_id"],
                "--resource-group",
                config["resource_group"],
                "--name",
                container_name,
            ],
            timeout_seconds=20,
        )
        parsed = _parse_logs(logs)

        runtime_ms = parsed.get("runtime_ms")
        if runtime_ms is None:
            runtime_ms = int((time.perf_counter() - overall_started) * 1000)

        return {
            "status": parsed.get("status", "error"),
            "stdout": parsed.get("stdout", ""),
            "stderr": parsed.get("stderr", ""),
            "runtime_ms": runtime_ms,
            "exit_code": parsed.get("exit_code"),
            "timed_out": bool(parsed.get("timed_out", False)),
            "detail": "" if parsed.get("status") == "accepted" else parsed.get("stderr", ""),
            "container_state": current_state,
        }
    except Exception as exc:
        logger.exception("ACI execution failed for container %s", container_name)
        return {
            "status": "error",
            "stdout": "",
            "stderr": str(exc),
            "runtime_ms": int((time.perf_counter() - overall_started) * 1000),
            "exit_code": None,
            "timed_out": False,
            "detail": str(exc),
        }
    finally:
        if container_created:
            try:
                _run_az(
                    [
                        "container",
                        "delete",
                        "--subscription",
                        config["subscription_id"],
                        "--resource-group",
                        config["resource_group"],
                        "--name",
                        container_name,
                        "--yes",
                        "--no-wait",
                    ],
                    timeout_seconds=20,
                )
            except Exception:
                logger.warning("Failed to delete ACI container %s", container_name, exc_info=True)
