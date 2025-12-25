@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ========================================
REM MyNote 停止服务脚本
REM ========================================

color 0C
title MyNote 停止服务

echo ========================================
echo  MyNote 停止服务
echo ========================================
echo.
echo 正在停止服务...
echo.

set "KILLED=0"

REM 尝试通过窗口标题停止
echo [检查] 查找 MyNote 后端窗口...
tasklist /FI "WINDOWTITLE eq MyNote Backend*" 2>nul | find /I "cmd.exe" >nul
if %errorlevel% equ 0 (
    echo [停止] 后端服务窗口...
    taskkill /FI "WINDOWTITLE eq MyNote Backend*" /F >nul 2>&1
    set "KILLED=1"
)

echo [检查] 查找 MyNote 前端窗口...
tasklist /FI "WINDOWTITLE eq MyNote Frontend*" 2>nul | find /I "cmd.exe" >nul
if %errorlevel% equ 0 (
    echo [停止] 前端服务窗口...
    taskkill /FI "WINDOWTITLE eq MyNote Frontend*" /F >nul 2>&1
    set "KILLED=1"
)

REM 等待一下
timeout /t 1 /nobreak >nul

REM 尝试停止可能残留的 Node.js 进程（监听5173端口）
echo [检查] 查找 Node.js 进程（端口5173）...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173"') do (
    if "%%a" neq "" (
        echo [停止] Node.js 进程 (PID: %%a)...
        taskkill /PID %%a /F >nul 2>&1
        set "KILLED=1"
    )
)

REM 尝试停止可能残留的 Python 进程（监听8000端口）
echo [检查] 查找 Python 进程（端口8000）...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000"') do (
    if "%%a" neq "" (
        echo [停止] Python 进程 (PID: %%a)...
        taskkill /PID %%a /F >nul 2>&1
        set "KILLED=1"
    )
)

echo.
if %KILLED% equ 1 (
    echo ========================================
    echo  服务已停止
    echo ========================================
) else (
    echo ========================================
    echo  未发现运行中的服务
    echo ========================================
)
echo.

pause
