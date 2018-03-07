@echo off

python --version
if %errorlevel%==9009 (
    START backend/python-2.7.14.msi
)

pip install -U -r backend/requirements.txt

cd backend

python main.py

pause
