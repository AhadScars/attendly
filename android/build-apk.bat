@echo off
setlocal
cd /d "%~dp0"
set "JAVA_HOME=C:\Program Files\Java\jdk-17"
set "ANDROID_HOME=C:\Users\Shoaib Qazi\AppData\Local\Android\Sdk"
set "ANDROID_SDK_ROOT=%ANDROID_HOME%"
call gradlew.bat assembleRelease --no-daemon
if errorlevel 1 exit /b 1
copy /Y "app\build\outputs\apk\release\app-release.apk" "..\Attendly-Parent.apk"
echo Built Attendly-Parent.apk
endlocal
