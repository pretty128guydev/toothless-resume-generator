@echo off
setlocal

set PROJECT_DIR=C:\Users\Administrator\generate\
set CLIENT_DIR=D:\Projects\Jobbids\client\
set SERVER_DIR=D:\Projects\Jobbids\server\
set EXT_SERVER_DIR=D:\Projects\Extension\job-scraper-extension\server\

if not exist "%PROJECT_DIR%api_server.py" (
  echo Could not find api_server.py at %PROJECT_DIR%.
  pause
  exit /b 1
)

if not exist "%CLIENT_DIR%package.json" (
  echo Could not find package.json at %CLIENT_DIR%.
  pause
  exit /b 1
)

if not exist "%SERVER_DIR%package.json" (
  echo Could not find package.json at %SERVER_DIR%.
  pause
  exit /b 1
)

if not exist "%EXT_SERVER_DIR%package.json" (
  echo Could not find package.json at %EXT_SERVER_DIR%.
  pause
  exit /b 1
)

cd /d %PROJECT_DIR%

if not exist .venv\Scripts\python.exe (
  echo Creating virtual environment...
  python -m venv .venv
)

call .venv\Scripts\python.exe -m pip install -r requirements.txt

REM Ensure Playwright browsers are installed
call .venv\Scripts\python.exe -m playwright install

REM Start the API server
echo Starting API server at http://127.0.0.1:8000 ...
start "API Server" .venv\Scripts\python.exe -m uvicorn api_server:app --reload

REM Start the client app
echo Starting client app at %CLIENT_DIR% ...
start "Client App" cmd /c "cd /d %CLIENT_DIR% && npm run start"

REM Start the server app
echo Starting server app at %SERVER_DIR% ...
start "Server App" cmd /c "cd /d %SERVER_DIR% && npm run dev"

REM Start the extension server app
echo Starting extension server app at %EXT_SERVER_DIR% ...
start "Extension Server" cmd /c "cd /d %EXT_SERVER_DIR% && npm run dev"

endlocal
