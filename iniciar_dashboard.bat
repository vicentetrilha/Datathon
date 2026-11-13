@echo off
title Monitor Estrategico - Datathon SENAI SC
cd /d "%~dp0"

echo ========================================================
echo   Iniciando Monitor Estrategico (Datathon SENAI SC)...
echo ========================================================
echo.

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo Abrindo painel em http://localhost:8501 ...
echo (Mantenha esta janela preta aberta enquanto usar o site)
echo.

where streamlit >nul 2>nul
if %errorlevel% equ 0 (
    streamlit run app.py --browser.gatherUsageStats false --server.headless false
) else (
    python -m streamlit run app.py --browser.gatherUsageStats false --server.headless false
    if %errorlevel% neq 0 (
        py -m streamlit run app.py --browser.gatherUsageStats false --server.headless false
    )
)

echo.
pause