@echo off
setlocal
cd /d "%~dp0.."

echo.
echo  CYBER OPS — yerel gelistirme (runserver + RQ worker)
echo  ----------------------------------------------------
echo  Gereksinim: MySQL + Redis calisiyor olmali
echo    scripts\start_infra.bat   VEYA   mevcut docker konteynerleri
echo.

echo [1/2] RQ worker ayri pencerede baslatiliyor...
start "CYBER OPS — RQ Worker" cmd /k "%~dp0start_local_worker.bat"

echo [2/2] Django runserver (bu pencere)...
timeout /t 2 /nobreak >nul

if exist env\Scripts\activate.bat (
    call env\Scripts\activate.bat
)

python manage.py runserver

echo.
echo runserver kapandi. Worker penceresini de kapatabilirsiniz.
pause
