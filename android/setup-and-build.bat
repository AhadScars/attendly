@echo off
cd /d "%~dp0"
echo Building Attendly parent APK...
call gradlew.bat assembleRelease --no-daemon
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)
copy /Y "app\build\outputs\apk\release\app-release.apk" "..\Attendly-Parent.apk"
echo.
echo APK: attendly-app\Attendly-Parent.apk
echo Also: android\app\build\outputs\apk\release\app-release.apk
