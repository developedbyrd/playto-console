#!/bin/bash

# Run migrations
python manage.py migrate --noinput

# WARNING: This will DELETE all data and re-seed
# Uncomment the next line to flush database (remove when done)
python manage.py flush --noinput

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
