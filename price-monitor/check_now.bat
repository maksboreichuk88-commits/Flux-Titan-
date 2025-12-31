@echo off
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
  echo Virtual env not found. Run setup.bat first.
  exit /b 1
)

.venv\Scripts\python.exe price_monitor.py --once

echo.
echo OK: One-time check completed.
echo.
