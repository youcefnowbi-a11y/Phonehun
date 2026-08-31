@echo off
title DroidCommand — Android Control Dashboard
echo ========================================================
echo        DROIDCOMMAND - ANDROID CONTROL DASHBOARD
echo ========================================================
echo.
echo [*] Lancement du serveur DroidCommand...
echo [*] Ouverture du tableau de bord dans votre navigateur...
echo.

start "" "http://127.0.0.1:5000"
python app.py

pause
