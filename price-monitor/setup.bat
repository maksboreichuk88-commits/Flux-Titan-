@echo off
echo Установка Price Monitor...
cd /d "%~dp0"

if not exist .env (
    echo Создаю .env из .env.example...
    copy .env.example .env
)

python -m venv .venv
if not exist .venv\Scripts\python.exe (
  echo Не удалось создать virtual env.
  exit /b 1
)

.venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo Готово! Теперь отредактируй .env и targets.json, затем запустите:
echo run.bat
echo.
pause
