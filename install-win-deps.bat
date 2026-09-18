@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
pip install -r requirements.txt
python -c "from supabase import create_client; print('supabase ok')"
