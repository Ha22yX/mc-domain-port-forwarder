@echo off
chcp 65001 > nul
cd /d "%~dp0.."

REM Generate start_hidden.vbs silently if it does not exist yet
if not exist "port_forwarder\start_hidden.vbs" (
    python -c "from port_forwarder.service_manager import generate_run_vbs; generate_run_vbs()" > nul 2>&1
)

echo Starting MC Domain Port Forwarder...
echo.
python -m port_forwarder.main
pause
