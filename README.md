The worker is part of the "The Hive" project, which queries the server for tasks and executes them.

## RELEASE PLAN:
1. Create requirements.txt:
  pip freeze > requirements.txt
2. Build exe:
  pyinstaller --onefile --clean main.py --name worker
3. Create worker.zip with worker.exe and updater.bat