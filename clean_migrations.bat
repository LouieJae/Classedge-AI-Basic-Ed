@echo off
echo Cleaning migration files...

REM List of app migration directories
set MIGRATION_DIRS=^
accounts\migrations ^
activity\migrations ^
calendars\migrations ^
classroom\migrations ^
coil\migrations ^
course\migrations ^
gradebookcomponent\migrations ^
logs\migrations ^
message\migrations ^
module\migrations ^
roles\migrations ^
subject\migrations

REM Loop through each directory and delete migration files except __init__.py
for %%d in (%MIGRATION_DIRS%) do (
    echo Processing %%d...
    for %%f in ("%%d\*.py") do (
        if /I not "%%~nxf"=="__init__.py" (
            echo Deleting %%f
            del "%%f"
        )
    )
)

echo.
echo Migration files cleaned successfully!
echo Only __init__.py files remain in migration folders.
echo.
pause
