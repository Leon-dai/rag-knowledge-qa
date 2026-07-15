@echo off
chcp 65001 >nul
echo ============================================
echo   企业级 RAG 知识库问答系统 - 一键启动
echo ============================================
echo.

:: 检查 Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.12+
    pause
    exit /b 1
)

:: 检查 Node.js
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [警告] 未找到 npm，前端将无法启动
)

echo [1/4] 安装后端依赖...
cd /d "%~dp0..\backend"
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [错误] 后端依赖安装失败
    pause
    exit /b 1
)
echo       后端依赖安装完成

echo [2/4] 安装前端依赖...
cd /d "%~dp0..\frontend"
call npm install
if %errorlevel% neq 0 (
    echo [错误] 前端依赖安装失败
    pause
    exit /b 1
)
echo       前端依赖安装完成

echo [3/4] 启动后端服务 (FastAPI)...
cd /d "%~dp0..\backend"
start "RAG-Backend" cmd /k "title 后端服务 && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
echo       后端服务已启动: http://127.0.0.1:8000

echo [4/4] 启动前端服务 (React + Vite)...
cd /d "%~dp0..\frontend"
start "RAG-Frontend" cmd /k "title 前端服务 && npm run dev"
echo       前端服务已启动: http://localhost:5173

echo.
echo ============================================
echo   启动完成！
echo   前端地址: http://localhost:5173
echo   API 文档: http://127.0.0.1:8000/docs
echo   管理员账号: admin / 123456
echo ============================================
echo.
echo 按任意键退出此窗口（不会关闭服务）
pause >nul
