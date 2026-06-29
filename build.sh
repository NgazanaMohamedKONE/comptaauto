#!/usr/bin/env bash
# Script de build pour Render
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Creer le super admin si pas existant
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@comptaauto.ci').exists():
    User.objects.create_user(
        email='admin@comptaauto.ci',
        username='admin',
        password='Admin2026!',
        first_name='KONE',
        last_name='MOHAMED',
        role='SUPER_ADMIN',
        is_staff=True,
        is_superuser=True,
    )
    print('Super admin cree')
"

# Init forfaits
python manage.py shell -c "
from abonnements.models import init_forfaits
init_forfaits()
print('Forfaits initialises')
"
