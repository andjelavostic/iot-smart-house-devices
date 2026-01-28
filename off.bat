@echo off
taskkill /F /IM python.exe /T

docker-compose stop

echo Sve ugaseno.
pause