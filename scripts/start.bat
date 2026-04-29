@echo off
title Smokey's Radio

rem Project directory - edit this path if you move the repo
set "PROJECT_DIR=C:\Users\vjpov\Codebase\Smokeys-Radio"

if not exist "%PROJECT_DIR%\bot.py" (
  echo ERROR: bot.py not found in %PROJECT_DIR%
  echo Edit PROJECT_DIR in this script if you moved the repo.
  pause
  exit /b 1
)

cd /d "%PROJECT_DIR%"

py -3 bot.py || python bot.py
pause
