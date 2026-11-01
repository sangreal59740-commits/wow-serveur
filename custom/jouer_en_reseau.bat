@echo off
chcp 65001 >nul
rem Permet de jouer depuis un autre PC de la maison : annonce l'adresse réseau de ce PC au lieu de 127.0.0.1
rem et ouvre les ports du serveur (3724 et 8085) dans le pare-feu Windows. A lancer une seule fois, base de données allumée.
net session >nul 2>&1
if errorlevel 1 (
  echo  Demande des droits administrateur pour le pare-feu...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
set "SPP=C:\SPP_Classics V2\SPP_Classics_V2\SPP_Server\Server\Database"
set "IP="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "$c = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null -and $_.NetAdapter.Status -eq 'Up' } | Select-Object -First 1; if ($c) { $c.IPv4Address[0].IPAddress }"`) do set "IP=%%i"
echo %IP%| findstr /r "^[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$" >nul
if errorlevel 1 (
  echo  Adresse réseau non trouvée automatiquement.
  set /p "IP=Tape l'adresse IPv4 de ce PC (ipconfig), puis Entree : "
)
echo %IP%| findstr /r "^[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$" >nul
if errorlevel 1 (
  echo  ERREUR : adresse invalide, rien n'a ete modifie.
  goto fin
)
echo.
echo  Adresse de ce PC sur le réseau : %IP%
echo.
"%SPP%\bin\mysql.exe" --defaults-extra-file="%SPP%\connection.cnf" --database=classicrealmd -e "UPDATE realmlist SET address='%IP%'; SELECT id, name, address, port FROM realmlist;"
if errorlevel 1 (
  echo  ERREUR base de données : envoie une capture a Claude.
  goto fin
)
netsh advfirewall firewall delete rule name="WoW serveur (connexion)" >nul 2>&1
netsh advfirewall firewall delete rule name="WoW serveur (monde)" >nul 2>&1
netsh advfirewall firewall add rule name="WoW serveur (connexion)" dir=in action=allow protocol=TCP localport=3724 >nul
netsh advfirewall firewall add rule name="WoW serveur (monde)" dir=in action=allow protocol=TCP localport=8085 >nul
echo  Pare-feu : ports 3724 et 8085 ouverts.
echo.
echo  Sur l'autre PC, mets dans C:\wow\realmlist.wtf la ligne :
echo      set realmlist %IP%
echo  Sur CE PC, rien a changer.
echo  Puis redémarre le serveur.
:fin
echo.
pause
