# The Hive Worker

## Overview
The worker is a client-side executable component of the "The Hive" distributed task system. Its primary function is to communicate with the central server, retrieve assigned tasks, execute them in an isolated environment, and return the results of the execution.

The application is designed for autonomous operation and supports a self-updating mechanism.

## Configuration
All primary operational parameters of the worker are centralized in the `config.py` file.

- **WORKER_VERSION**: The semantic version of the worker build. This must be updated for each new release to ensure the proper functioning of the update mechanism.
- **SERVER_URL**: The root URL of the server's API endpoint.
- **TASK_REGISTRY**: A dictionary that maps task string identifiers (as received from the server) to their corresponding executable function objects within the codebase.
- **NO_TASK_SLEEP**: The time interval in seconds the worker waits before making a new request to the server if no tasks are available.
- **TIME_ERROR_SLEEP**: The time interval in seconds the worker waits before retrying a connection after a network error.

## Adding a New Task
The architecture supports the modular addition of new tasks through the following steps:

1. **Implement Task Logic**: Create a new Python file within the `tasks/` directory. This file should contain the function that implements the logic for the new task.
2. **Import the Function**: In `config.py`, add an import statement to make the new task function available.

```python
from tasks.new_task_module import new_task_function
```

3. **Register the Task**: In `config.py`, add a new key-value pair to the `TASK_REGISTRY` dictionary. The key is the string identifier the server will use, and the value is the imported function object.

```python
TASK_REGISTRY = {
    "prom_pars": prom_parser_task,
    "new_task_name": new_task_function
}
```

## Development Setup
To run the worker in a local development environment, follow these steps:

1. **Create a Virtual Environment**:

```bash
python -m venv venv
```

2. **Activate the Environment**:
    - On Windows:

    ```bash
    .\venv\Scripts\activate
    ```

    - On macOS/Linux:

    ```bash
    source venv/bin/activate
    ```

3. **Install Dependencies**: First, ensure you have an up-to-date `requirements.txt` file, then install from it.

```bash
pip freeze > requirements.txt
pip install -r requirements.txt
```

4. **Run the Application**:

```bash
python main.py
```

## Build and Release Process
Creating a distributable release involves the following sequence:

1. **Update Version**: Increment the `WORKER_VERSION` constant in `config.py`.
2. **Freeze Dependencies**: Update the list of required packages.

```bash
pip freeze > requirements.txt
```

3. **Build Executable**: Compile the project into a single executable file using PyInstaller. The `--clean` flag is recommended to remove cached files from previous builds.

```bash
pyinstaller --onefile --clean main.py --name worker
```

4. **Create Release Archive**: Package the necessary files into a `.zip` archive for distribution. The archive must contain:

   - `worker.exe` (the compiled application)
   - `updater.bat` (the self-update script)