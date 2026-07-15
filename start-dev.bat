@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%void-system-backend"
set "FRONTEND_DIR=%ROOT_DIR%void-system-frontend"

if not exist "%BACKEND_DIR%\main.py" (
  echo [ERROR] Backend entry point not found: "%BACKEND_DIR%\main.py"
  pause
  exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
  echo [ERROR] Frontend package file not found: "%FRONTEND_DIR%\package.json"
  pause
  exit /b 1
)

where uv >nul 2>nul
if errorlevel 1 (
  echo [ERROR] uv is not available on PATH. Install uv before starting the backend.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm is not available on PATH. Install Node.js before starting the frontend.
  pause
  exit /b 1
)

echo Starting Void System backend...
start "Void System Backend" cmd /k "cd /d ""%BACKEND_DIR%"" && uv run main.py"

echo Starting Void System frontend...
start "Void System Frontend" cmd /k "cd /d ""%FRONTEND_DIR%"" && npm run dev"

echo Development terminals opened.
exit /b 0
