@echo off
chcp 65001 > nul
title DigitalOcean Canlı Sunucuya Yükleme - ŞimşekLog OS
cd /d "%~dp0"

powershell.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0sunucu_yukle.ps1"
