@echo off
chcp 65001 >nul
set "SPP=C:\SPP_Classics V2\SPP_Classics_V2\SPP_Server\Server\Database"
echo.
echo  Classes custom : creation, sorts, maitres de classe, talents, recolte...
echo  (la base doit etre lancee : option 2 du menu SPP)
echo.
"%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos < "%~dp0classes.sql"
if errorlevel 1 goto erreur
"%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos < "%~dp0sorts.sql"
if errorlevel 1 goto erreur
"%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos < "%~dp0recolte.sql"
if errorlevel 1 goto erreur
if exist "%~dp0primes_bas.sql" (
  "%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos < "%~dp0primes_bas.sql"
  if errorlevel 1 goto erreur
)
if exist "%~dp0primes_evenements.sql" (
  "%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos < "%~dp0primes_evenements.sql"
  if errorlevel 1 goto erreur
)
if exist "%~dp0primes_eau.sql" (
  "%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos < "%~dp0primes_eau.sql"
  if errorlevel 1 goto erreur
)
if exist "%~dp0primes_xp.sql" (
  "%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos < "%~dp0primes_xp.sql"
  if errorlevel 1 goto erreur
)
if exist "%~dp0maisons.sql" (
  "%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos < "%~dp0maisons.sql"
  if errorlevel 1 goto erreur
)
if exist "%~dp0logement.sql" (
  "%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos < "%~dp0logement.sql"
  if errorlevel 1 goto erreur
)
if exist "%~dp0modes.sql" (
  "%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos < "%~dp0modes.sql"
  if errorlevel 1 goto erreur
)
if exist "%~dp0tableaux.sql" (
  "%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos < "%~dp0tableaux.sql"
  if errorlevel 1 goto erreur
)
if exist "%~dp0reliques.sql" (
  "%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos < "%~dp0reliques.sql"
  if errorlevel 1 goto erreur
)
if exist "%~dp0marqueurs.sql" (
  "%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classicmangos < "%~dp0marqueurs.sql"
  if errorlevel 1 goto erreur
)
if exist "%~dp0reset_talents.sql" (
  "%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --default-character-set=utf8mb4 --database=classiccharacters < "%~dp0reset_talents.sql"
  if errorlevel 1 goto erreur
  del "%~dp0reset_talents.sql"
)
echo. & echo  Termine. Redemarre le serveur.
goto fin
:erreur
echo. & echo  ERREUR : envoie une capture a Claude.
:fin
echo.
pause
