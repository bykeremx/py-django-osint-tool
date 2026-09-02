@echo off
cd /d "%~dp0.."
docker compose --profile infra --profile app down
echo Stack durduruldu.
pause
