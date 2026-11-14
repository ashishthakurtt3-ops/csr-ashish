@echo off
cd /d "D:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)"
call .venv\Scripts\activate.bat
python manage.py runserver 127.0.0.1:8000 --insecure