#!/usr/bin/env python
"""
Create superuser if it doesn't exist
Run during deployment to ensure admin access
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User

username = 'aseeb'
email = 'admin@lapoaitools.com'
password = 'Dr.aseeb123'

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'✓ Superuser "{username}" created successfully')
else:
    print(f'✓ Superuser "{username}" already exists')
