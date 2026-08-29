@echo off
color 0A
echo =====================================================================
echo    SIH 2024: Blockchain-Based Digital Evidence Management System
echo =====================================================================
echo.

:: Check Prerequisites
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH! Please install Python.
    pause
    exit /b
)

node --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js is not installed or not in PATH! Please install Node.js.
    pause
    exit /b
)

echo [1/3] Setting up Python Backend Environment...
cd backend
IF NOT EXIST ".venv" (
    echo Creating Virtual Environment...
    python -m venv .venv
)
call .venv\Scripts\activate
echo Installing Python Dependencies...
pip install -r requirements.txt
echo Installing NLP Model (spaCy)...
python -m spacy download en_core_web_md
cd ..

echo.
echo [2/3] Setting up Node.js Frontend...
cd frontend
call npm install
cd ..

echo.
echo [3/3] Launching Servers...
echo Starting Backend (FastAPI)...
start "SIH Backend" cmd /k "cd backend && call .venv\Scripts\activate && uvicorn main:app --reload --port 8000"

echo Starting Frontend (Next.js)...
start "SIH Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo =====================================================================
echo  SUCCESS! Both servers are starting up.
echo  Frontend will be available at: http://localhost:3000
echo  Backend API Docs: http://localhost:8000/docs
echo =====================================================================
echo Note: Ensure Tesseract-OCR is installed on your Windows machine for PDF scanning.
pause
