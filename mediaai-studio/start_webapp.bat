@echo off
title MediaAI Corp — Web App
echo.
echo  ============================================
echo   MediaAI Corp -- Your AI-Powered Media Empire
echo  ============================================
echo.
echo  Installation des dependances...
pip install Flask -q
echo.
echo  Demarrage du serveur...
echo  Ouvrir votre navigateur sur : http://localhost:5000
echo.
cd /d "%~dp0"
python webapp\app.py
pause
