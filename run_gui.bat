@echo off
REM ==============================================================================
REM ARXML SecDiff - Windows GUI Launcher
REM Double-click this file or run from cmd:
REM   run_gui.bat          (Starts Next.js GUI on http://localhost:3000)
REM   run_gui.bat python   (Starts Python GUI on http://localhost:8080)
REM ==============================================================================

cd /d "%~dp0"

echo ==========================================================
echo            ARXML SecDiff - GUI Launcher                  
echo ==========================================================

if "%1"=="python" goto run_python
if "%1"=="py" goto run_python
if "%1"=="8080" goto run_python

:run_next
echo Starting Interactive Next.js Web GUI on http://localhost:3000...
cd web_gui\next-app
pnpm dev --port 3000
goto end

:run_python
echo Starting Python Lightweight GUI on http://localhost:8080...
python pipeline_gui\server.py
goto end

:end
