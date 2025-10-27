@echo off
REM Batch script untuk menjalankan Aplikasi Absensi di Windows
REM Double-click file ini untuk menjalankan aplikasi

title Aplikasi Absensi
echo.
echo ========================================
echo    APLIKASI ABSENSI - STARTING...
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python tidak terinstall!
    echo Silakan install Python terlebih dahulu dari https://python.org
    echo.
    pause
    exit /b 1
)

REM Check if app.py exists
if not exist "app.py" (
    echo ERROR: File app.py tidak ditemukan!
    echo Pastikan file ini berada di folder yang sama dengan app.py
    echo.
    pause
    exit /b 1
)

REM Run the launcher
echo Memulai aplikasi...
python run_aplikasi.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Aplikasi berhenti dengan error.
    pause
)

echo.
echo Aplikasi selesai.
pause
