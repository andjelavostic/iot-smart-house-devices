@echo off
echo Gasenje Python procesa...
taskkill /F /IM python.exe /T

echo Zaustavljanje Docker kontejnera...
docker-compose stop

echo Sve ugaseno.
pause