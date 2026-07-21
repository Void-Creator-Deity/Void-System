@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%void-system-backend"
set "FRONTEND_DIR=%ROOT_DIR%void-system-frontend"
set "BACKEND_PYTHON=%BACKEND_DIR%\.venv313\Scripts\python.exe"

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

set "NODE_EXE="
for /f "delims=" %%I in ('where node 2^>nul') do if not defined NODE_EXE set "NODE_EXE=%%I"
if not defined NODE_EXE (
  echo [ERROR] Node.js is not available on PATH. Install Node.js before starting the frontend.
  pause
  exit /b 1
)

for %%I in ("%NODE_EXE%") do set "NODE_DIR=%%~dpI"
set "NPM_CLI=%NODE_DIR%node_modules\npm\bin\npm-cli.js"
if not exist "%NPM_CLI%" (
  echo [ERROR] The npm CLI bundled with Node.js was not found: "%NPM_CLI%"
  pause
  exit /b 1
)

echo Starting Void System backend...
if exist "%BACKEND_PYTHON%" (
  start "Void System Backend" /D "%BACKEND_DIR%" cmd /k ""%BACKEND_PYTHON%" main.py"
) else (
  where uv >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Backend runtime not found. Expected "%BACKEND_PYTHON%" or uv on PATH.
    pause
    exit /b 1
  )
  start "Void System Backend" /D "%BACKEND_DIR%" cmd /k "uv run main.py"
)

echo Starting Void System frontend...
start "Void System Frontend" /D "%FRONTEND_DIR%" cmd /k ""%NODE_EXE%" "%NPM_CLI%" run dev -- --host 127.0.0.1"

echo Development terminals opened.
exit /b 0
