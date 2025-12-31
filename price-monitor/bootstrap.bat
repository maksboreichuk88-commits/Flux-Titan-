@echo off
cd /d "%~dp0"
echo === 1) Setup ===
call setup.bat

echo.
echo === 2) Configure .env ===
call configure.bat
