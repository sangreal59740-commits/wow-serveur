@echo off
chcp 65001 >nul
title Portail
cd /d "%~dp0"
echo  Portail : site, inscription et launcher.
echo  La base SPP doit etre lancee (option 2 du menu SPP).
echo.
Portail.exe
pause
