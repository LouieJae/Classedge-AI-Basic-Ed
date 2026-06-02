@echo off
echo Creating migrations in the specified order...

REM Activate the virtual environment
call env\Scripts\activate.bat

REM Create migrations in the specified order
echo.
echo Step 1: Creating migrations for roles...
python manage.py makemigrations roles
if %errorlevel% neq 0 goto error

echo.
echo Step 2: Creating migrations for accounts...
python manage.py makemigrations accounts
if %errorlevel% neq 0 goto error

echo.
echo Step 3: Creating migrations for subject...
python manage.py makemigrations subject
if %errorlevel% neq 0 goto error

echo.
echo Step 4: Creating migrations for course...
python manage.py makemigrations course
if %errorlevel% neq 0 goto error

echo.
echo Step 5: Creating migrations for module...
python manage.py makemigrations module
if %errorlevel% neq 0 goto error

echo.
echo Step 6: Creating migrations for activity...
python manage.py makemigrations activity
if %errorlevel% neq 0 goto error

echo.
echo Step 7: Creating migrations for gradebookcomponent...
python manage.py makemigrations gradebookcomponent
if %errorlevel% neq 0 goto error

REM Create migrations for remaining apps
echo.
echo Step 8: Creating migrations for remaining apps...
python manage.py makemigrations calendars classroom coil logs message social_media
if %errorlevel% neq 0 goto error

echo.
echo All migrations created successfully!
echo.
echo Would you like to apply these migrations now? (Y/N)
set /p apply_migrations="Apply migrations (Y/N)? "
if /I "%apply_migrations%"=="Y" (
    echo.
    echo Applying migrations...
    python manage.py migrate
    echo.
    echo Migrations applied successfully!
) else (
    echo.
    echo Migrations created but not applied. Run 'python manage.py migrate' when ready.
)

goto end

:error
echo.
echo Error occurred during migration creation. Please check the output above.
pause
exit /b 1

:end
echo.
echo Migration process completed.
pause
