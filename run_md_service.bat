@echo off
chcp 65001 >nul
setlocal

REM ===================================================================
REM MD TO EMBEDDINGS SERVICE v4.0 - Simple Reliable Launcher
REM ===================================================================

title MD to Embeddings Service v4.0

cd /d "%~dp0"
color 0A

set PYTHON_SCRIPT=md_to_embeddings_service_v4.py

echo.
echo ===================================================================
echo                MD TO EMBEDDINGS SERVICE v4.0
echo ===================================================================
echo Working directory: %CD%
echo ===================================================================
echo.

REM Simple Python check
echo [1/2] Checking Python...
py --version >nul 2>&1
if errorlevel 1 goto :no_py_launcher

echo Python launcher found
py --version
set PY_CMD=py
goto :python_ok

:no_py_launcher
echo Python launcher not found, trying python command...
python --version >nul 2>&1
if errorlevel 1 goto :no_python

echo Python command found
python --version
set PY_CMD=python
goto :python_ok

:no_python
echo.
echo ERROR: Python not found!
echo.
echo Please install Python from:
echo - https://python.org
echo - Microsoft Store (search "Python")
echo.
pause
exit /b 1

:python_ok
echo Python check completed successfully
echo.

REM Check main script exists
echo [2/2] Checking main script...
if exist "%PYTHON_SCRIPT%" (
    echo Main script found: %PYTHON_SCRIPT%
) else (
    echo.
    echo ERROR: %PYTHON_SCRIPT% not found!
    echo Please make sure the file exists in the current directory.
    echo.
    pause
    exit /b 1
)
echo.

REM Launch service
echo ===================================================================
echo Launching MD to Embeddings Service v4.0...
echo ===================================================================
echo.
echo MENU OPTIONS:
echo   1. Deploy project template (first run)
echo   2. Convert DRAKON schemas
echo   3. Create .md file (WITHOUT service files)
echo   4. Copy .md to Dropbox
echo   5. Exit
echo.
echo ===================================================================
echo.

%PY_CMD% "%PYTHON_SCRIPT%"
set EXIT_CODE=%errorlevel%

echo.
echo ===================================================================
if %EXIT_CODE% equ 0 (
    echo Service completed successfully
) else (
    echo Service exited with code: %EXIT_CODE%
)
echo ===================================================================
echo.
pause
exit /b %EXIT_CODE%