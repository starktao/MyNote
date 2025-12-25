@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

REM ========================================
REM MyNote 项目一键启动脚本
REM ========================================

set "PROJECT_ROOT=%~dp0"
set "FRONTEND_DIR=%PROJECT_ROOT%1211front"
set "BACKEND_DIR=%PROJECT_ROOT%newbackend"
REM 自动检测合适的 Python 版本 (3.8+)
set "PYTHON_CMD="

color 0A
title MyNote 项目启动器

echo ========================================
echo  MyNote 项目启动器
echo ========================================
echo.
echo 正在检查环境...
echo.

REM 环境检测
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo  错误: 缺少 Node.js
    echo ========================================
    echo.
    echo 请手动安装 Node.js 后重试
    echo 下载地址: https://nodejs.org/
    echo.
    pause
    exit /b 1
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo  错误: 缺少 Python
    echo ========================================
    echo.
    echo 请手动安装 Python 后重试
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM 智能检测 Python 版本 (3.8+)
echo [检测] Python 版本...

REM 尝试多个 Python 命令，按优先级顺序
set "PYTHON_CANDIDATES=python python3 py"
set "FOUND_PYTHON="

for %%p in (%PYTHON_CANDIDATES%) do (
    if not defined FOUND_PYTHON (
        %%p --version >nul 2>&1
        if !errorlevel! equ 0 (
            for /f "tokens=2" %%v in ('%%p --version 2^>^&1') do set TEST_VERSION=%%v
            for /f "tokens=1,2 delims=." %%a in ("!TEST_VERSION!") do (
                set MAJOR=%%a
                set MINOR=%%b
            )
            if !MAJOR! equ 3 (
                if !MINOR! geq 9 (
                    set "FOUND_PYTHON=%%p"
                    set "PYTHON_VERSION=!TEST_VERSION!"
                )
            )
        )
    )
)

if not defined FOUND_PYTHON (
    goto :python_version_error
)

set "PYTHON_CMD=%FOUND_PYTHON%"
echo [找到] Python %PYTHON_VERSION% (命令: %PYTHON_CMD%)
goto :python_version_ok

:python_version_error
    echo.
    echo ========================================
    echo  错误: 未找到合适的 Python 版本
    echo ========================================
    echo.
    echo 要求版本: Python 3.9 或更高
    echo.
    echo 系统中检测到的 Python 命令：
    for %%p in (%PYTHON_CANDIDATES%) do (
        %%p --version >nul 2>&1
        if !errorlevel! equ 0 (
            for /f "tokens=2" %%v in ('%%p --version 2^>^&1') do echo   - %%p: %%v
        ) else (
            echo   - %%p: 未安装
        )
    )
    echo.
    echo 请安装 Python 3.8 或更高版本后重试
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1

:python_version_ok

echo [OK] 环境检查通过 (Python %PYTHON_VERSION%)
echo.

REM 检查依赖是否已安装
echo [检查] 项目依赖...
set "NEED_FRONTEND=0"
set "NEED_BACKEND=0"

if not exist "%FRONTEND_DIR%\node_modules" (
    echo [!] 前端依赖未安装
    set "NEED_FRONTEND=1"
)

REM 每次启动都安装后端依赖（确保环境正确）
echo [安装] 后端依赖（每次启动都会更新）...
echo.
cd /d "%BACKEND_DIR%"
%PYTHON_CMD% -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo  错误: 后端依赖安装失败
    echo ========================================
    echo.
    cd /d "%PROJECT_ROOT%"
    pause
    exit /b 1
)
cd /d "%PROJECT_ROOT%"
echo [OK] 后端依赖安装完成
echo.

REM 验证关键依赖是否可用
echo [验证] 检查依赖...
%PYTHON_CMD% -c "import fastapi; import faster_whisper; import openai; import easyocr" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo  错误: 依赖验证失败
    echo ========================================
    echo.
    echo 虽然安装成功，但部分模块无法导入
    echo 请检查 Python 版本和网络连接
    echo.
    pause
    exit /b 1
)
echo [OK] 依赖验证通过
echo.

REM 如果依赖完整，配置环境后启动
if %NEED_FRONTEND% equ 0 (
    echo [OK] 前端依赖已安装
    echo.
    goto :config_env
)

REM 自动安装依赖
echo.
echo ========================================
echo  开始安装依赖
echo ========================================
echo.

REM 安装前端依赖
if %NEED_FRONTEND% equ 1 (
    echo [安装] 前端依赖...
    echo 这可能需要几分钟，请耐心等待...
    echo.
    cd /d "%FRONTEND_DIR%"
    call npm install
    REM 检查 node_modules 是否存在来判断安装是否成功
    if not exist "%FRONTEND_DIR%\node_modules" (
        echo.
        echo [错误] 前端依赖安装失败
        cd /d "%PROJECT_ROOT%"
        pause
        exit /b 1
    )
    cd /d "%PROJECT_ROOT%"
    echo [OK] 前端依赖安装完成
    echo.
)

echo ========================================
echo  依赖安装完成！
echo ========================================
echo.
echo [继续] 启动服务...
echo.
goto :config_env

:config_env
REM 配置环境变量
if not exist "%FRONTEND_DIR%\.env" (
    copy "%FRONTEND_DIR%\.env.example" "%FRONTEND_DIR%\.env" >nul 2>&1
)

if not exist "%BACKEND_DIR%\.env" (
    copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul 2>&1
)

REM 检查 ffmpeg 是否安装
echo [检查] ffmpeg...
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] ffmpeg 未安装
    echo.
    echo ========================================
    echo  需要安装 ffmpeg
    echo ========================================
    echo.
    echo ffmpeg 是音视频处理工具，必需安装
    echo.
    echo 请选择安装方式：
    echo   1. 打开下载页面（推荐）
    echo   2. 跳过（可能导致转写失败）
    echo.
    set /p FFCHOICE="请选择 (1/2): "

    if /i "!FFCHOICE!"=="1" (
        echo.
        echo [下载] 正在打开 ffmpeg 下载页面...
        echo.
        echo 请按以下步骤安装：
        echo   1. 下载 ffmpeg（选择 Windows 64-bit 版本）
        echo   2. 解压到 C:\ffmpeg
        echo   3. 将 C:\ffmpeg\bin 添加到系统 PATH
        echo   4. 重新打开命令行窗口
        echo.
        start https://www.gyan.dev/ffmpeg/builds/
        echo.
        pause
        exit /b 1
    )
    echo [警告] 跳过 ffmpeg 安装，转写功能可能无法使用
    echo.
) else (
    echo [OK] ffmpeg 已安装
)
echo.

REM 检查模型是否可用（首次运行会自动下载）
echo [检查] AI 模型...
echo.
echo 注意: 首次运行时会自动下载 Whisper 模型（约 500MB）
echo       请确保网络连接正常
echo.
%PYTHON_CMD% -c "from faster_whisper import WhisperModel; model = WhisperModel('small', device='cpu', compute_type='int8'); print('[OK] Whisper 模型可用')" 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo  错误: Whisper 模型检测失败
    echo ========================================
    echo.
    echo 可能的原因:
    echo   1. 网络连接问题，无法下载模型
    echo   2. 磁盘空间不足
    echo   3. 防火墙/代理设置阻止了下载
    echo.
    echo 请检查网络连接后重试
    echo.
    pause
    exit /b 1
)
echo.

:start_services
REM 启动服务
echo.
echo ========================================
echo  正在启动服务...
echo ========================================
echo.

echo [启动] 后端服务 (端口 8000)...
start "MyNote Backend" cmd /k "cd /d "%BACKEND_DIR%" && %PYTHON_CMD% start_server.py"

echo [等待] 后端服务启动中...
timeout /t 5 /nobreak >nul

echo [启动] 前端服务 (端口 5173)...
start "MyNote Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev"

echo [等待] 前端服务启动中...
timeout /t 5 /nobreak >nul

echo [浏览器] 正在打开应用...
timeout /t 2 /nobreak >nul
start http://localhost:5173

echo.
echo ========================================
echo  服务启动完成！
echo ========================================
echo.
echo  前端地址: http://localhost:5173
echo  后端地址: http://localhost:8000
echo  API文档:  http://localhost:8000/docs
echo.
echo  提示: 关闭此窗口不会停止服务
echo        请分别关闭前后端窗口来停止服务
echo.
echo 按任意键关闭此窗口（服务将继续运行）...
pause >nul
