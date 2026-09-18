@echo off
cd /d "%~dp0"
echo Building Attendly.exe ...
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)
pip install pyinstaller
pyinstaller --noconfirm --clean ^
  --name Attendly ^
  --onefile ^
  --console ^
  --add-data "app/templates;app/templates" ^
  --add-data "app/static;app/static" ^
  --hidden-import=openpyxl ^
  --hidden-import=firebase_admin ^
  --hidden-import=google.oauth2 ^
  --hidden-import=supabase ^
  --hidden-import=supabase._sync ^
  --hidden-import=supabase._sync.client ^
  --hidden-import=postgrest ^
  --hidden-import=httpx ^
  --hidden-import=dotenv ^
  main.py

echo.
echo Done. EXE is in dist\Attendly.exe
echo On first run a data\ folder is created next to the EXE.
pause
