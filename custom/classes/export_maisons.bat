@echo off
chcp 65001 >nul
set "SPP=C:\SPP_Classics V2\SPP_Classics_V2\SPP_Server\Server\Database"
echo.
echo  Export du reperage des maisons pour Claude...
"%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos -B -e "SELECT * FROM custom_maison" > "%~dp0maisons_export.tsv"
"%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos -B -e "SELECT * FROM custom_maison_pnj" > "%~dp0maisons_pnj_export.tsv"
echo.
echo  Termine : maisons_export.tsv et maisons_pnj_export.tsv. Previens Claude.
pause
