@echo off
title Monitor Estrategico - Datathon SENAI SC
cd /d "%~dp0"

echo ========================================================
echo   Iniciando Monitor Estrategico (Datathon SENAI SC)...
echo ========================================================
echo.

if exist ".venv\Scripts\activate.bat" (
    echo Ativando ambiente virtual (.venv)...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo Ativando ambiente virtual (venv)...
    call venv\Scripts\activate.bat
)

echo Abrindo painel no navegador (http://localhost:8501)...
echo Pressione Ctrl + C neste terminal para encerrar.
echo.

python -m streamlit run app.py
pause