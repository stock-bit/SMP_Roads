@echo off
setlocal enabledelayedexpansion
title Push Rewari SMP Road Cleaning Circles to GitHub

echo =====================================================================
echo  Rewari Municipal Council - Push to Git Repository
echo =====================================================================
echo.

:: 1. Check if Git is installed
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git is not found in your system PATH!
    echo.
    echo Would you like to automatically install Git using Windows Package Manager?
    set /p INSTALL_GIT="Install Git now? (Y/N): "
    if /i "!INSTALL_GIT!"=="Y" (
        echo Installing Git... Please wait.
        winget install --id Git.Git -e --source winget
        echo.
        echo Git installed! Please restart your terminal/command prompt and run this script again.
        pause
        exit /b 0
    ) else (
        echo Please install Git manually from https://git-scm.com/download/win and run this script again.
        pause
        exit /b 1
    )
)

echo [1/5] Checking Git repository initialization...
if not exist ".git" (
    echo Initializing new Git repository...
    git init -b main
) else (
    echo Git repository already initialized.
    git branch -M main
)

echo.
echo [2/5] Staging files to Git...
git add .

echo.
echo [3/5] Creating commit...
git commit -m "Initial commit: Municipal Council Rewari - 30 SMP Road Cleaning Circles & Staff Allotment GIS" 2>nul
if %errorlevel% neq 0 (
    echo Working tree already clean or commit made.
)

echo.
echo [4/5] GitHub Repository Configuration...

:: Check if GitHub CLI is installed and logged in
where gh >nul 2>nul
if %errorlevel% equ 0 (
    echo GitHub CLI (gh) detected!
    echo Choose an option:
    echo  [1] Automatically create a NEW GitHub repository and push
    echo  [2] Push to an EXISTING GitHub repository URL
    set /p GH_CHOICE="Enter choice (1 or 2): "

    if "!GH_CHOICE!"=="1" (
        set /p REPO_NAME="Enter new repository name [default: rewari-smp-cleaning-circles]: "
        if "!REPO_NAME!"=="" set REPO_NAME=rewari-smp-cleaning-circles
        echo Creating public repository !REPO_NAME! and pushing...
        gh repo create !REPO_NAME! --public --source=. --remote=origin --push
        if %errorlevel% equ 0 (
            echo.
            echo =====================================================================
            echo [SUCCESS] Repository created and pushed successfully to GitHub!
            echo =====================================================================
            pause
            exit /b 0
        )
    )
)

:: Option for manual GitHub URL
echo.
git remote get-url origin >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%u in ('git remote get-url origin') do set CURRENT_ORIGIN=%%u
    echo Current remote origin: !CURRENT_ORIGIN!
    set /p USE_EXISTING="Push to this existing remote? (Y/N): "
    if /i "!USE_EXISTING!"=="Y" (
        goto PUSH_REMOTE
    )
)

echo Please enter your GitHub repository URL.
echo (Example: https://github.com/your-username/rewari-smp-circles.git)
set /p REPO_URL="GitHub Repository URL: "

if "!REPO_URL!"=="" (
    echo [ERROR] No repository URL provided. Aborting.
    pause
    exit /b 1
)

git remote remove origin 2>nul
git remote add origin !REPO_URL!

:PUSH_REMOTE
echo.
echo [5/5] Pushing to GitHub (main branch)...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo =====================================================================
    echo [SUCCESS] Successfully pushed all files to GitHub!
    echo =====================================================================
) else (
    echo.
    echo [NOTE] Push failed. If the remote repository has files (like README/License),
    echo run: git pull origin main --rebase
    echo and then try pushing again.
)

echo.
pause
