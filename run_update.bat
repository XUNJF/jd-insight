@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
if not exist "D:\code\jd-insight\logs" mkdir "D:\code\jd-insight\logs"
cd /d D:\code\jd-insight
D:\code\python-practice\day46-47\venv\Scripts\python.exe update.py >> "D:\code\jd-insight\logs\update.log" 2>&1