@echo off
echo Starting Candidate Summary Generator...
echo.

echo Starting Backend API...
start cmd /k "cd backend && python app.py"

echo Waiting for backend to start...
timeout /t 3 /nobreak > nul

echo Starting Frontend...
start cmd /k "npm run dev"

echo.
echo Both services are starting!
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:5000
echo.
echo Press any key to exit...
pause > nul
