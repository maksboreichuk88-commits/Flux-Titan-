@echo off
cd /d "%~dp0"

if not exist .venv (
  echo Virtual env not found. Run setup.bat first.
  exit /b 1
)

if not exist .venv\Scripts\python.exe (
  echo Virtual env is broken. Re-run setup.bat.
  exit /b 1
)

.venv\Scripts\python.exe configure_env.py

echo.
echo Готово. Теперь можешь запускать мониторинг:
echo   run.bat
echo.
pause
