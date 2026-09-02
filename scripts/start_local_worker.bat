@echo off
cd /d "%~dp0.."
if exist env\Scripts\activate.bat (
    call env\Scripts\activate.bat
)
echo RQ worker starting (Windows SimpleWorker — no fork)...
python manage.py rqworker default --worker-class rq.worker.SimpleWorker
