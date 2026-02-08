#!/bin/bash

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Seed database
echo "Seeding database..."
python manage.py seed_admin

# Start server
echo "Starting server..."
exec "$@"
