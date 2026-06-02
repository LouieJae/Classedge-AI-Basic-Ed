@echo off
echo Setting up virtual environment for ClassEdge LMS...

REM Create a virtual environment
python -m venv env

REM Activate the virtual environment
call env\Scripts\activate.bat

REM Install requirements
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo.
echo Environment setup complete!
echo.
echo To activate the environment in the future, run:
echo     call env\Scripts\activate.bat
echo.
echo To deactivate the environment when done, run:
echo     deactivate
echo.
pause
