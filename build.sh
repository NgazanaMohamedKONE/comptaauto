#!/usr/bin/env bash
# Script de build adapté pour Vercel et Render
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --noinput

# Creer le super admin si pas existant
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@comptaauto.ci').exists():
    User.objects.create_superuser(
        email='admin@comptaauto.ci',
        username='admin',
        password='Admin2026!',
        first_name='KONE',
        last_name='MOHAMED',
        role='SUPER_ADMIN'
    )
    print('Super admin cree')
"

# Init forfaits
python manage.py shell -c "
from abonnements.models import init_forfaits
try:
    init_forfaits()
    print('Forfaits initialises')
except Exception as e:
    print('Erreur init forfaits:', e)
"
