@echo off
REM ---------------------------------------------------------------------------
REM Launcher for auto_ut. Double-click this (or run it) instead of calling
REM python directly, so the console window STAYS OPEN after it finishes and you
REM can read the results. Any args are passed through, e.g.:
REM     run.bat --ask
REM     run.bat --skip-flash
REM ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"

python autotest.py %*
set RC=%ERRORLEVEL%

echo.
echo ============================================================
echo  autotest finished, exit code = %RC%   ( 0 = all PASS )
echo  results : _ut_work\results\result.json
echo  full log: _ut_work\logs\
echo ============================================================
pause
exit /b %RC%
