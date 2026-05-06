@echo off
REM One-click demo launcher.
REM Double-click this file. It calls start.ps1 with execution policy bypassed
REM so you don't have to mess with PowerShell security settings.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
