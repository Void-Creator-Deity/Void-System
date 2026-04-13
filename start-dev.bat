@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%void-system-backend"
set "FRONTEND_DIR=%ROOT_DIR%void-system-frontend"

if not exist "%BACKEND_DIR%\main.py" (
  echo [ERROR] 未找到后端入口: "%BACKEND_DIR%\main.py"
  pause
  exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
  echo [ERROR] 未找到前端项目: "%FRONTEND_DIR%\package.json"
  pause
  exit /b 1
)

echo 正在启动后端终端...
start "Void System Backend" cmd /k "cd /d ""%BACKEND_DIR%"" && uv run main.py"

echo 正在启动前端终端...
start "Void System Frontend" cmd /k "cd /d ""%FRONTEND_DIR%"" && npm run dev"

echo 已打开两个终端窗口。
exit /b 0
