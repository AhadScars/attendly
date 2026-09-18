@echo off
cd /d "%~dp0"
echo.
echo  Parent phone School server:
echo      http://192.168.1.8:5055
echo  Same Wi-Fi. If sign-in fails, run open-phone-access.bat as Admin.
echo.
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)
python main.py
