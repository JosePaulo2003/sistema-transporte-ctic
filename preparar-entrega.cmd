@echo off
cd /d "%~dp0"
python comandos\entrega.py
if errorlevel 1 (
    echo A entrega foi bloqueada. Confira as mensagens acima.
    pause
    exit /b 1
)
pause
