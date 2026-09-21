@echo off
chcp 65001 > nul
title ŞimşekLog OS v5.0 - Komuta Merkezi
cd /d "%~dp0"
echo ============================================================
echo   ⚡ ŞimşekLog OS v5.0 - Enterprise Lojistik Komuta Masası
echo   Tarayıcınız otomatik olarak açılacaktır...
echo ============================================================
set PORT=8000
python -m uvicorn app:app --host 0.0.0.0 --port %PORT%
pause
