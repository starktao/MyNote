@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ========================================
REM MyNote 快速启动脚本
REM （环境已配置的情况下使用）
REM ========================================

REM 设置项目根目录
set "PROJECT_ROOT=%~dp0"
set "FRONTEND_DIR=%PROJECT_ROOT%1211front"
set "BACKEND_DIR=%PROJECT_ROOT%newbackend"

REM 设置颜色和标题
color 0B
title MyNote 快速启动

echo ========================================
echo  MyNote 快速启动
echo ========================================
echo.
echo 正在启动服务...
echo.

REM 启动后端服务（新窗口）
echo [启动] 后端服务 (端口 8000)...
start "MyNote Backend" cmd /k "cd /d "%BACKEND_DIR%" && title MyNote Backend && python start_server.py"

REM 等待后端启动
echo [等待] 后端服务启动中...
timeout /t 3 /nobreak >nul

REM 启动前端服务（新窗口）
echo [启动] 前端服务 (端口 5173)...
start "MyNote Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && title MyNote Frontend && npm run dev"

REM 等待前端启动
echo [等待] 前端服务启动中...
timeout /t 5 /nobreak >nul

REM 自动打开浏览器
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
echo 按任意键关闭此窗口...
pause >nul
