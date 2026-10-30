@echo off
setlocal
cd /d "%~dp0"
set "READER_PYTHON=.venv\Scripts\python.exe"
if not exist "%READER_PYTHON%" if exist "..\.venv\Scripts\python.exe" set "READER_PYTHON=..\.venv\Scripts\python.exe"
if not exist "%READER_PYTHON%" (
    py -3 -m venv .venv
    if errorlevel 1 goto failed
)
"%READER_PYTHON%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 'Manga Reader requires Python 3.12 or newer. Recreate .venv with a supported Python version.')"
if errorlevel 1 goto failed
"%READER_PYTHON%" -c "from PySide6.QtPdf import QPdfDocument" >nul 2>&1
if errorlevel 1 (
    "%READER_PYTHON%" -m pip install -r requirements.txt
    if errorlevel 1 goto failed
)
"%READER_PYTHON%" main.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Could not start Manga Reader. See the error above.
echo Install Python 3.12 or newer from python.org if Python is missing.
pause
exit /b 1
