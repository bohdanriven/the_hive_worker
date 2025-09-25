import requests
import time
import uuid
import subprocess
import tempfile
import json
import os
import base64

# CONFIG
SERVER_URL = "http://127.0.0.1:3010"
WORKER_ID = f"worker_{uuid.uuid4().hex[:6]}"
NO_TASK_SLEEP = 60  # timeout in case of no tasks
TIME_ERROR_SLEEP = 60  # timeout in case of connection error
HEADERS = {"X-Worker-ID": WORKER_ID}


# Function executes received tasks and returns (success, output)
def execute_task(task: dict) -> tuple[bool, str]:
    task_type = task.get("task_type")
    timeout = task.get("timeout_seconds", 60)

    try:
        # If task is a command, run it and return its console output
        if task_type == "command":
            command = task.get("command")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                shell=True,
                check=True,
                timeout=timeout,
            )
            return True, result.stdout.strip()

        # If task is a file, run it and return its result
        elif task_type == "file":
            # Get file encoded content
            content_base64 = task.get("file_content")
            if not content_base64:
                return False, "ERROR: File content is empty"

            ext = task.get("file_extension", "tmp")

            try:
                # Decode Base64 into binary data
                binary_content = base64.b64decode(content_base64)

                # Create a temporary binary file ('wb' mode)
                with tempfile.NamedTemporaryFile(
                    mode="wb", delete=False, suffix=f".{ext}"
                ) as tmp_file:
                    tmp_file.write(binary_content)
                    script_path = tmp_file.name

                # Execute the file directly
                command_to_run = script_path

                result = subprocess.run(
                    command_to_run,
                    capture_output=True,
                    text=True,
                    shell=True,
                    check=True,
                    timeout=timeout,
                    encoding="utf-8",
                    errors="ignore",
                )
                return True, result.stdout.strip()
            finally:
                # Guaranteed to delete temporary files
                if "script_path" in locals() and os.path.exists(script_path):
                    os.remove(script_path)

        # If task type is unknown
        else:
            return False, f"Type of task is unknown: {task_type}"

    except subprocess.TimeoutExpired:
        return False, f"ERROR: The execution time ({timeout}s) has expired."
    except subprocess.CalledProcessError as e:
        return False, f"ERROR: Process failed.\nSTDERR: {e.stderr.strip()}"
    except Exception as e:
        return False, f"ERROR: Failed to complete task: {e}"


# Function is an infinite loop that performs the work of a worker — receiving, executing, and returning tasks.
def main_loop():
    print(f"Worker {WORKER_ID} is running. Connecting to {SERVER_URL}...")

    while True:
        try:
            # Task receiving
            response = requests.get(
                f"{SERVER_URL}/get_task", headers=HEADERS, timeout=10
            )
            response.raise_for_status()
            task = response.json()

            # If there are no tasks, wait and try again
            if task.get("status") == "no_tasks":
                time.sleep(NO_TASK_SLEEP)
                continue
            print(f"Task {task['id']} (type: {task['task_type']}) received")

            # Task execution
            is_successful, output = execute_task(task)

            # Prepare the final data for sending
            status = "success" if is_successful else "failure"
            output_str = output.strip()
            final_result = output_str  # By default, what the script returned

            # Check if the returned result is a PATH TO AN EXISTING FILE
            if is_successful and os.path.isfile(output_str):
                try:
                    # If so, read the contents of this file
                    with open(output_str, "r", encoding="utf-8") as f:
                        final_result = json.load(
                            f
                        )  # and this content becomes the final result
                except (json.JSONDecodeError, IOError) as e:
                    # If the file could not be read or parsed, consider it an error
                    status = "failure"
                    final_result = f"Error processing result file: {e}"
                finally:
                    os.remove(output_str)

            # Form the payload with the CORRECT data
            result_payload = {
                "task_id": task["id"],
                "worker_id": WORKER_ID,
                "status": status,
                "result": final_result,
            }

            requests.post(
                f"{SERVER_URL}/submit_result", json=result_payload, timeout=30
            ).raise_for_status()
            print(
                f"Task {result_payload['task_id']} returned with status: {result_payload['status']}"
            )

        except requests.exceptions.RequestException as e:
            print(
                f"ERROR: Server access error: {e}. Timeout {TIME_ERROR_SLEEP} seconds."
            )
            time.sleep(TIME_ERROR_SLEEP)
        except Exception as e:
            print(
                f"CRITICAL ERROR: An unexpected error occurred: {e}. Timeout {TIME_ERROR_SLEEP} seconds."
            )
            time.sleep(TIME_ERROR_SLEEP)


if __name__ == "__main__":
    main_loop()
