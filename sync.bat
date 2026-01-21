@echo off
REM Synchronization helper script for SpectralEdge (Windows)
REM This script simplifies the process of syncing your local changes with GitHub

REM Ensure the script is run from the project root
cd /d "%~dp0"

echo === SpectralEdge Sync Tool ===
echo.

REM Check if git is installed
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo Git is not installed or not in PATH. Please install Git to continue.
    exit /b 1
)

REM Function dispatcher
if "%1"=="" goto usage
if /i "%1"=="pull" goto pull_changes
if /i "%1"=="push" goto push_changes
if /i "%1"=="status" goto show_status
if /i "%1"=="sync" goto full_sync
goto unknown_command

:usage
echo Usage: sync.bat [command]
echo.
echo Commands:
echo   pull    - Pull latest changes from GitHub
echo   push    - Commit all changes and push to GitHub
echo   status  - Show current git status
echo   sync    - Pull, then commit and push all changes (full sync)
echo.
exit /b 0

:pull_changes
echo Pulling latest changes from GitHub...
git pull origin main
if %errorlevel% equ 0 (
    echo Successfully pulled latest changes
) else (
    echo Failed to pull changes. Please resolve any conflicts.
    exit /b 1
)
goto end

:push_changes
REM Check if there are any changes to commit
git status --porcelain > nul 2>&1
if %errorlevel% neq 0 (
    echo No changes to commit.
    goto end
)

echo Staging all changes...
git add .

echo.
set /p commit_msg="Enter commit message (or press Enter for default): "

if "%commit_msg%"=="" (
    for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set mydate=%%c-%%a-%%b
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do set mytime=%%a:%%b
    set commit_msg=Update: %mydate% %mytime%
)

echo Committing changes...
git commit -m "%commit_msg%"

echo Pushing to GitHub...
git push origin main

if %errorlevel% equ 0 (
    echo Successfully pushed changes to GitHub
) else (
    echo Failed to push changes. Please check your connection and credentials.
    exit /b 1
)
goto end

:show_status
echo Current git status:
echo.
git status
goto end

:full_sync
call :pull_changes
echo.
call :push_changes
goto end

:unknown_command
echo Unknown command: %1
echo.
goto usage

:end
