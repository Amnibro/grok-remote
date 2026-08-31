@echo off
:loop
python "%~dp0motion_service.py" >> "%~dp0motion_service.%COMPUTERNAME%.log" 2>&1
timeout /t 3 /nobreak >nul
goto loop
