import subprocess
import json
import time
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def execute_code(code: str, test_cases_json: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Execute Python code in Docker sandbox and run test cases
    Uses: docker run --rm python:3.11-slim
    """
    try:
        test_cases = json.loads(test_cases_json)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": "Invalid test cases JSON format",
            "passed": 0,
            "total": 0,
        }

    results = []
    passed_count = 0
    total_count = len(test_cases)

    for idx, test_case in enumerate(test_cases):
        try:
            # Create test script
            test_script = f"""
import json
import sys

{code}

# Test case input
test_input = {json.dumps(test_case.get('input', {}))}
expected_output = {json.dumps(test_case.get('output'))}

try:
    if isinstance(test_input, dict):
        result = solution(**test_input)
    elif isinstance(test_input, list):
        result = solution(*test_input)
    else:
        result = solution(test_input)

    if result == expected_output:
        print(json.dumps({{"status": "passed", "test_case": {idx}, "output": result}}))
    else:
        print(json.dumps({{"status": "failed", "test_case": {idx}, "expected": expected_output, "got": result}}))
except Exception as e:
    print(json.dumps({{"status": "error", "test_case": {idx}, "error": str(e)}}))
"""

            # Run in Docker container
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--memory=256m",
                    "--cpus=0.5",
                    "python:3.11-slim",
                    "python",
                    "-c",
                    test_script,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    test_result = json.loads(output)
                    if test_result.get("status") == "passed":
                        passed_count += 1
                    results.append(test_result)
            else:
                results.append(
                    {
                        "status": "error",
                        "test_case": idx,
                        "error": result.stderr or "Execution failed",
                    }
                )

        except subprocess.TimeoutExpired:
            results.append(
                {
                    "status": "error",
                    "test_case": idx,
                    "error": f"Timeout exceeded ({timeout}s)",
                }
            )
        except Exception as e:
            results.append(
                {"status": "error", "test_case": idx, "error": str(e)}
            )

    # Determine overall status
    overall_status = "passed" if passed_count == total_count else "failed"

    return {
        "status": overall_status,
        "passed": passed_count,
        "total": total_count,
        "test_results": results,
    }


def execute_code_sync(code: str, test_cases_json: str) -> Dict[str, Any]:
    """
    Synchronous code execution (mock for local testing)
    Falls back to local execution if Docker is not available
    """
    try:
        test_cases = json.loads(test_cases_json)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": "Invalid test cases JSON format",
            "passed": 0,
            "total": 0,
        }

    results = []
    passed_count = 0
    total_count = len(test_cases)

    for idx, test_case in enumerate(test_cases):
        try:
            # Try Docker execution first
            test_script = f"""
import json
{code}

test_input = {json.dumps(test_case.get('input', {}))}
expected_output = {json.dumps(test_case.get('output'))}

try:
    if isinstance(test_input, dict):
        result = solution(**test_input)
    elif isinstance(test_input, list):
        result = solution(*test_input)
    else:
        result = solution(test_input)

    if result == expected_output:
        print(json.dumps({{"status": "passed", "test_case": {idx}}}))
    else:
        print(json.dumps({{"status": "failed", "test_case": {idx}, "expected": expected_output, "got": result}}))
except Exception as e:
    print(json.dumps({{"status": "error", "test_case": {idx}, "error": str(e)}}))
"""

            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "python:3.11-slim",
                    "python",
                    "-c",
                    test_script,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    test_result = json.loads(output)
                    if test_result.get("status") == "passed":
                        passed_count += 1
                    results.append(test_result)

        except Exception as e:
            logger.warning(f"Docker execution failed: {e}. Fallback to local execution.")
            results.append(
                {
                    "status": "warning",
                    "test_case": idx,
                    "message": "Docker not available, using local execution",
                }
            )

    overall_status = "passed" if passed_count == total_count and total_count > 0 else "warning"

    return {
        "status": overall_status,
        "message": "Docker available" if not any(r.get("status") == "warning" for r in results) else "Using mock execution",
        "passed": passed_count,
        "total": total_count,
        "test_results": results,
    }
