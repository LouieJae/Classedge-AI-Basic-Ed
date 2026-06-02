#!/bin/bash

echo "Cleaning migration files..."
echo ""

# List of app migration directories
MIGRATION_DIRS=(
    "accounts/migrations"
    "activity/migrations"
    "calendars/migrations"
    "classroom/migrations"
    "coil/migrations"
    "course/migrations"
    "gradebookcomponent/migrations"
    "logs/migrations"
    "message/migrations"
    "module/migrations"
    "roles/migrations"
    "subject/migrations"
)

# Loop through each directory and delete migration files except __init__.py
for dir in "${MIGRATION_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "Processing $dir..."
        find "$dir" -type f -name "*.py" ! -name "__init__.py" -delete
        echo "  ✓ Cleaned"
    else
        echo "  ⚠ Directory not found: $dir"
    fi
done

echo ""
echo "Migration files cleaned successfully!"
echo "Only __init__.py files remain in migration folders."
echo ""
