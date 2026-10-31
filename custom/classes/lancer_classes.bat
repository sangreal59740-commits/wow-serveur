@echo off
chcp 65001 >nul
set "SPP=C:\SPP_Classics V2\SPP_Classics_V2\SPP_Server\Server\Database"
echo.
echo  Classes custom (creation : Necromancien, Sniper, Metamorphe)...
echo  (la base doit etre lancee : option 2 du menu SPP)
echo.
"%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos < "%~dp0classes.sql"
if errorlevel 1 (echo. & echo  ERREUR : envoie une capture a Claude.) else (echo. & echo  Termine. Redemarre le serveur.)
echo.
pause
