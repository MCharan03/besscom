@echo off
title BESCOM Smart Meter AI — Starting...
color 0A

echo.
echo  ================================================
echo   BESCOM Smart Meter AI — Startup
echo   Demand Forecasting + Anomaly Detection Platform
echo  ================================================
echo.

REM Check if synthetic data exists
if not exist "backend\data\feeders.parquet" (
    echo  [1/3] Generating synthetic Bengaluru meter data...
    echo        This runs once and takes ~30 seconds.
    echo.
    cd backend
    python data_generator.py
    if %ERRORLEVEL% NEQ 0 (
        echo  ERROR: Data generation failed. Check Python/pip installation.
        pause
        exit /b 1
    )
    cd ..
    echo.
    echo  [1/3] Synthetic data generated successfully.
) else (
    echo  [1/3] Synthetic data already exists. Skipping generation.
)

echo.
echo  [2/3] Starting FastAPI backend on http://localhost:8000 ...
start "BESCOM Backend" cmd /k "cd backend && uvicorn main:app --reload --port 8000 --host 0.0.0.0"

echo.
echo  [3/3] Starting React frontend on http://localhost:5173 ...
timeout /t 3 /nobreak >nul
start "BESCOM Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo  ================================================
echo   Both servers are starting!
echo.
echo   Dashboard:  http://localhost:5173
echo   API Docs:   http://localhost:8000/docs
echo  ================================================
echo.
timeout /t 5 /nobreak >nul
start http://localhost:5173
