import os
import sys
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comptaauto.settings')

# Initialisation normale de l'application Django
application = get_wsgi_application()

# --- Bloc d'auto-migration pour les environnements Serverless (Vercel) ---
from django.core.management import call_command

try:
    print("Début de l'exécution automatique des migrations...")
    call_command('migrate', interactive=False)
    print("Migrations terminées avec succès !")
except Exception as e:
    print(f"Erreur lors de l'exécution des migrations : {e}", file=sys.stderr)
# -------------------------------------------------------------------------
