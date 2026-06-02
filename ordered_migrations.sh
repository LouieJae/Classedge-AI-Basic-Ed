#!/bin/bash

echo "Creating migrations in the specified order..."

# Activate the virtual environment
source env/bin/activate

# Function to create migrations for an app and exit on error
create_migrations() {
    echo
    echo "Creating migrations for $1..."
    python manage.py makemigrations "$1"
    if [ $? -ne 0 ]; then
        echo "Error occurred while creating migrations for $1. Exiting."
        exit 1
    fi
}

# Ordered migrations
create_migrations roles
create_migrations accounts
create_migrations subject
create_migrations course
create_migrations module
create_migrations activity
create_migrations gradebookcomponent

# Remaining apps
echo
echo "Creating migrations for remaining apps..."
python manage.py makemigrations calendars classroom coil logs message social_media
if [ $? -ne 0 ]; then
    echo "Error occurred while creating migrations for remaining apps. Exiting."
    exit 1
fi

echo
read -p "All migrations created successfully! Apply migrations now? (Y/N) " apply_migrations
if [[ "$apply_migrations" =~ ^[Yy]$ ]]; then
    echo "Applying migrations..."
    python manage.py migrate
    echo "Migrations applied successfully!"
else
    echo "Migrations created but not applied. Run 'python manage.py migrate' when ready."
fi

echo "Migration process completed."
