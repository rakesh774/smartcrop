@echo off
title Agri-Direct Server
cd /d "%~dp0"
echo Starting Agri-Direct Portal...
echo.
timeout /t 2
start http://127.0.0.1:5000
".\.venv\Scripts\python.exe" main.py
