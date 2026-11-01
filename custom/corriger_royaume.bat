@echo off
chcp 65001 >nul
rem Remet l'adresse du royaume (vidée par erreur) : 192.168.1.180, adresse de ce PC sur le réseau
set "SPP=C:\SPP_Classics V2\SPP_Classics_V2\SPP_Server\Server\Database"
"%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --database=classicrealmd -e "UPDATE realmlist SET address='192.168.1.180'; SELECT id, name, address, port FROM realmlist;"
if errorlevel 1 (echo  ERREUR : envoie une capture a Claude.) else (echo  Adresse du royaume : 192.168.1.180. Redemarre le serveur.)
echo.
pause
