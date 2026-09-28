@echo off
setlocal EnableExtensions
pushd "%~dp0.."

if exist ".venv\Scripts\python.exe" goto use_venv
python -m streamlit run "ui\app.py" %*
goto finished

:use_venv
".venv\Scripts\python.exe" -m streamlit run "ui\app.py" %*

:finished
set "status=%ERRORLEVEL%"
popd
if "%status%"=="0" goto exit_script
echo.
echo Demo startup failed. Run: python -m pip install -r requirements.txt
pause

:exit_script
endlocal & exit /b %status%
