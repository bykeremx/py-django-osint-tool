@echo off
cd /d "%~dp0.."
echo [app] Full stack build + start...
docker compose --profile infra --profile app up --build -d
if errorlevel 1 exit /b 1
echo.
echo Web        : http://localhost:8000
echo phpMyAdmin : http://localhost:8080
echo.
docker compose --profile infra --profile app ps
pause
