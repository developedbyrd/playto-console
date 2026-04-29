#!/bin/bash

# Run migrations
python manage.py migrate --noinput

# Seed database (only if no merchants exist)
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.exists():
    from django.core.management import call_command
    call_command('seed')
    print("Database seeded successfully")
else:
    print("Database already has users, skipping seed")
EOF
