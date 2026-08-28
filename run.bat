@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
echo Starting Digital Evidence Locker Prototype...

echo [1/2] Starting Backend API...
echo Installing/verifying Python dependencies...
python -m pip install fastapi uvicorn sqlalchemy pydantic python-multipart pypdf scikit-learn numpy pytesseract Pillow --quiet

start cmd /k "cd backend && set PYTHONIOENCODING=utf-8 && python -m uvicorn main:app --reload"

echo Waiting for backend to start...
timeout /t 8 /nobreak

echo Initializing Dummy Data...
curl -s -X POST http://localhost:8000/setup-dummy-data/

echo Running AI Search Backfill...
curl -s -X POST http://localhost:8000/search/backfill/

echo [2/2] Starting Frontend UI...
start cmd /k "cd frontend && echo Installing Node dependencies... && npm install && npm run dev"

echo.
echo All services started!
echo Frontend UI:        http://localhost:3000
echo Backend API Docs:   http://localhost:8000/docs
echo.
echo Press any key to exit this window...
pause
