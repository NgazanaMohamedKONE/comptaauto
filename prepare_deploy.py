"""
COMPTAAUTO - Preparation pour deploiement Render
Genere tous les fichiers necessaires (Procfile, build.sh, requirements, etc.)
Usage: python prepare_deploy.py
"""
import os
import subprocess
from pathlib import Path

BASE = Path(__file__).parent

print("\n" + "="*65)
print("  PREPARATION DEPLOIEMENT RENDER")
print("="*65 + "\n")

if os.name == 'nt':
    PY = str(BASE / "venv" / "Scripts" / "python.exe")
    PIP = str(BASE / "venv" / "Scripts" / "pip.exe")
else:
    PY = str(BASE / "venv" / "bin" / "python")
    PIP = str(BASE / "venv" / "bin" / "pip")

# 1. Generer requirements.txt depuis le venv
print("[1/6] Generation requirements.txt...")
result = subprocess.run([PIP, "freeze"], capture_output=True, text=True)
with open(BASE / "requirements.txt", "w", encoding="utf-8") as f:
    f.write(result.stdout)
print("      OK\n")

# 2. Creer build.sh (script de build pour Render)
print("[2/6] Creation build.sh...")
build_sh = '''#!/usr/bin/env bash
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
'''
with open(BASE / "build.sh", "w", encoding="utf-8", newline='\n') as f:
    f.write(build_sh)
print("      OK\n")

# 3. Creer render.yaml (config Render Infrastructure as Code)
print("[3/6] Creation render.yaml...")
render_yaml = '''services:
  - type: web
    name: comptaauto
    env: python
    region: frankfurt
    plan: free
    buildCommand: "./build.sh"
    startCommand: "gunicorn comptaauto.wsgi:application"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.9
      - key: SECRET_KEY
        generateValue: true
      - key: DEBUG
        value: false
      - key: ALLOWED_HOSTS
        value: ".onrender.com"
      - key: DATABASE_URL
        fromDatabase:
          name: comptaauto-db
          property: connectionString
      - key: OCR_SPACE_API_KEY
        value: helloworld
      - key: WEB_CONCURRENCY
        value: 4

databases:
  - name: comptaauto-db
    region: frankfurt
    plan: free
'''
with open(BASE / "render.yaml", "w", encoding="utf-8") as f:
    f.write(render_yaml)
print("      OK\n")

# 4. Creer runtime.txt (version Python)
print("[4/6] Creation runtime.txt...")
with open(BASE / "runtime.txt", "w", encoding="utf-8") as f:
    f.write("python-3.11.9\n")
print("      OK\n")

# 5. Mettre a jour settings.py pour la production
print("[5/6] Mise a jour settings.py (production-ready)...")
settings_content = '''from pathlib import Path
import environ
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='dev-key-change-me-in-prod')
DEBUG = env('DEBUG', default=False)

# Hosts autorises (Render + localhost)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
# Ajouter le hostname Render automatiquement
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
ALLOWED_HOSTS.append('.onrender.com')

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')

INSTALLED_APPS = [
    'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes',
    'django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles',
    'accounts','comptabilite','ocr_app','dashboard',
    'rapprochement','reporting','alertes','communication','abonnements',
    'admin_panel',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'abonnements.middleware.AbonnementMiddleware',
]

ROOT_URLCONF = 'comptaauto.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
        'abonnements.middleware.context_abonnement',
    ]},
}]
WSGI_APPLICATION = 'comptaauto.wsgi.application'

# Database : PostgreSQL en prod, SQLite en local
DATABASE_URL = env('DATABASE_URL', default='')
if DATABASE_URL:
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=True)}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_USER_MODEL = 'accounts.User'
AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Abidjan'
USE_I18N = True
USE_TZ = True

# Static files (Whitenoise)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

OCR_SPACE_API_KEY = env('OCR_SPACE_API_KEY', default='helloworld')

# Securite production
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
'''

with open(BASE / "comptaauto" / "settings.py", "w", encoding="utf-8") as f:
    f.write(settings_content)
print("      OK\n")

# 6. Mettre a jour .gitignore
print("[6/6] Mise a jour .gitignore...")
gitignore = '''# Python
__pycache__/
*.pyc
*.pyo

# Virtualenv
venv/
env/

# Django
*.log
db.sqlite3
db.sqlite3-journal
media/factures/
media/backups/
staticfiles/

# Environment
.env
.env.local

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Backups & ML models
*.pkl
*.sqlite3

# Renders
.render/
'''
with open(BASE / ".gitignore", "w", encoding="utf-8") as f:
    f.write(gitignore)
print("      OK\n")

print("="*65)
print("  FICHIERS DE DEPLOIEMENT CREES !")
print("="*65)
print("\nFichiers generes :")
print("  - requirements.txt   (dependances)")
print("  - build.sh           (script build Render)")
print("  - render.yaml        (config Render)")
print("  - runtime.txt        (Python 3.11.9)")
print("  - settings.py        (mode production)")
print("  - .gitignore         (mis a jour)")
print("\nPROCHAINES ETAPES :")
print("  1. Initialiser Git :  git init")
print("  2. Creer compte GitHub")
print("  3. Pousser le code")
print("  4. Creer compte Render")
print("  5. Deployer !")
print("\nVoir le guide complet dans la conversation Claude")
print("="*65 + "\n")
