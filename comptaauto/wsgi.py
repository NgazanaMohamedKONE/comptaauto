import os
import sys
import threading
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comptaauto.settings')

# 1. Démarrage immédiat de l'application pour que le serveur web Vercel valide l'envol
application = get_wsgi_application()

# 2. Fonction exécutée en arrière-plan pour initialiser PostgreSQL
def run_db_initialization():
    try:
        print("Vercel arrière-plan : Début de l'exécution automatique des migrations...")
        call_command('migrate', interactive=False)
        print("Vercel arrière-plan : Migrations exécutées avec succès.")
        
        # Création du Super Admin si inexistant
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
            print("Vercel arrière-plan : Super admin créé.")
            
        # Initialisation des forfaits
        from abonnements.models import init_forfaits
        init_forfaits()
        print("Vercel arrière-plan : Forfaits initialisés avec succès.")
        
    except Exception as e:
        print(f"Erreur lors de l'initialisation de la base : {e}", file=sys.stderr)

# Lancement du thread asynchrone (Non bloquant pour l'invocation de la fonction)
threading.Thread(target=run_db_initialization, daemon=True).start()
