@echo off
title RAAZ FILES - One-time Install
cd /d "%~dp0"
echo ==================================================
echo    RAAZ FILES automation - ONE-TIME install
echo ==================================================
echo.
echo Step 1/2: Python libraries install ho rahi hain (2-5 min)...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run\setup.ps1"
echo.
echo Step 2/2: Daily auto-tasks schedule ho rahe hain.
echo   (Ek "User Account Control" / admin popup aayega - "Yes" dabao.)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','\"%~dp0run\install_tasks.ps1\"'"
echo.
echo ==================================================
echo    HO GAYA! Ab sab apne aap chalega:
echo      - roz 6:00 AM  : din ka topic
echo      - roz 12:00 PM : long video + 3 shorts upload
echo      - Somwar 10 AM : SEO report
echo.
echo    PowerShell dobara kholne ki ZAROORAT NAHI.
echo    Bas 12 PM ke waqt PC ON hona chahiye.
echo ==================================================
echo.
pause
