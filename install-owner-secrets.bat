@echo off
cd /d "%~dp0"
set "DEST=%LOCALAPPDATA%\Attendly"
mkdir "%DEST%" 2>nul
mkdir "%DEST%\firebase" 2>nul
if exist ".env" copy /Y ".env" "%DEST%\.env" >nul
if exist "data\firebase-adminsdk.json" copy /Y "data\firebase-adminsdk.json" "%DEST%\firebase\firebase-adminsdk.json" >nul
if exist "firebase\firebase-adminsdk.json" copy /Y "firebase\firebase-adminsdk.json" "%DEST%\firebase\firebase-adminsdk.json" >nul
echo Owner keys saved to:
echo   %DEST%\.env
echo   %DEST%\firebase\firebase-adminsdk.json
echo These stay on THIS Windows user. They are not inside Attendly-Share.
pause
