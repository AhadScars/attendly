@echo off
cd /d "%~dp0"
if not exist "dist\Attendly.exe" (
  echo Build Attendly.exe first: build_exe.bat
  pause
  exit /b 1
)
rmdir /s /q "Attendly-Share" 2>nul
mkdir Attendly-Share
copy /Y "dist\Attendly.exe" "Attendly-Share\Attendly.exe" >nul
(
  echo Attendly school copy
  echo.
  echo This folder has ONLY the program. No .env and no Firebase keys.
  echo.
  echo 1. Open Attendly.exe
  echo 2. Choose School PC
  echo 3. Enter the Attendly server URL the owner gave you
  echo    Example: http://192.168.1.8:5055
  echo.
  echo Do not ask the owner for .env or firebase-adminsdk.json.
) > "Attendly-Share\README.txt"
echo Ready: Attendly-Share\
echo Send only that folder. Do not send dist\
pause
