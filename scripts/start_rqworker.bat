@echo off
cd /d "%~dp0.."
call env\Scripts\activate.bat
python manage.py rqworker default --worker-class rq.worker.SimpleWorker
