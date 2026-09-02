@echo off
cd /d "%~dp0.."
echo [infra] MySQL + Redis + phpMyAdmin baslatiliyor...
docker compose --profile infra up -d
if errorlevel 1 exit /b 1
echo.
echo MySQL      : localhost:3306
echo Redis      : localhost:6379
echo phpMyAdmin : http://localhost:8080
echo.
echo Django     : py manage.py runserver
echo RQ Worker  : scripts\start_local_worker.bat
pause
