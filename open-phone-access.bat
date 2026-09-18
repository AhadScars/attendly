@echo off
:: Open TCP 5055 so a phone on the same Wi-Fi can reach Attendly.
net session >nul 2>&1
if not %errorlevel%==0 (
  echo Requesting Administrator to allow the phone through Windows Firewall...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

netsh advfirewall firewall delete rule name="Attendly5055" >nul 2>&1
netsh advfirewall firewall add rule name="Attendly5055" dir=in action=allow protocol=TCP localport=5055 profile=private,domain

echo.
echo Firewall is open on port 5055.
echo On the parent app, School server must be:
echo.
echo     http://192.168.1.8:5055
echo.
echo Phone and this PC must be on the same Wi-Fi.
echo Keep run.bat or Attendly.exe running.
echo.
pause
