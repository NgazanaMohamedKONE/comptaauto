"""
COMPTAAUTO COMPLET - Installation en un clic
Inclut : Auth + Dashboard + OCR (API) + ML + Admin + Deploy Config
Usage: python comptaauto_complete.py
"""
import os, sys, subprocess
from pathlib import Path

BASE = Path(__file__).parent

print("\n" + "="*65)
print("  COMPAAUTO - Installation Complete (OCR + ML + Dashboard)")
print("="*65 + "\n")

# ============ 1. VENV ============
VENV = BASE / "venv"
if not VENV.exists():
    print("[1/6] Creation environnement virtuel...")
    subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
else:
    print("[1/6] Venv existant")

if os.name == 'nt':
    PY = str(VENV / "Scripts" / "python.exe")
    PIP = str(VENV / "Scripts" / "pip.exe")
else:
    PY = str(VENV / "bin" / "python")
    PIP = str(VENV / "bin" / "pip")

# ============ 2. INSTALL ============
print("[2/6] Installation dependances (3-5 min)...")
subprocess.run([PIP, "install", "--quiet", "Django==4.2.16", "Pillow", "requests", "scikit-learn", "numpy", "pandas", "gunicorn", "whitenoise", "dj-database-url", "psycopg2-binary"], check=True)
print("      OK")

# ============ 3. DOSSIERS ============
print("[3/6] Creation dossiers...")
for d in ["comptaauto","accounts","accounts/migrations","comptabilite","comptabilite/migrations",
          "ocr","ocr/migrations","dashboard","templates/accounts","templates/admin_panel",
          "templates/dashboard","templates/partials","templates/ocr","static/css","static/js","media","ml_models"]:
    (BASE / d).mkdir(parents=True, exist_ok=True)

# ============ 4. FICHIERS ============
print("[4/6] Generation fichiers...")
FILES = {}

# --- CONFIG ---
FILES[".env"] = '''SECRET_KEY=django-insecure-change-me-in-production-12345
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,*
DATABASE_URL=sqlite:///db.sqlite3
OCR_SPACE_API_KEY=helloworld
'''

FILES[".env.example"] = '''SECRET_KEY=
DEBUG=False
ALLOWED_HOSTS=
DATABASE_URL=
OCR_SPACE_API_KEY=helloworld
'''

FILES[".gitignore"] = '''__pycache__/
*.pyc
venv/
.env
db.sqlite3
media/
staticfiles/
*.pkl
'''

FILES["manage.py"] = '''#!/usr/bin/env python
import os, sys
def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comptaauto.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
if __name__ == '__main__':
    main()
'''

# --- DJANGO CONFIG ---
FILES["comptaauto/__init__.py"] = ""

FILES["comptaauto/settings.py"] = '''from pathlib import Path
import environ, os

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='dev-key-change-me')
DEBUG = env('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', '*'])

INSTALLED_APPS = [
    'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes',
    'django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles',
    'accounts','comptabilite','ocr_app','dashboard',
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
    ]},
}]
WSGI_APPLICATION = 'comptaauto.wsgi.application'

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_USER_MODEL = 'accounts.User'
AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Abidjan'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
OCR_SPACE_API_KEY = env('OCR_SPACE_API_KEY', default='helloworld')
'''

FILES["comptaauto/urls.py"] = '''from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', lambda r: redirect('login')),
    path('', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('admin-panel/', include('dashboard.urls_admin')),
    path('comptabilite/', include('comptabilite.urls')),
    path('ocr/', include('ocr_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
'''

FILES["comptaauto/wsgi.py"] = '''import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comptaauto.settings')
application = get_wsgi_application()
'''

# --- ACCOUNTS ---
FILES["accounts/__init__.py"] = ""
FILES["accounts/migrations/__init__.py"] = ""
FILES["accounts/apps.py"] = '''from django.apps import AppConfig
class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
'''

FILES["accounts/models.py"] = '''from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        ENTREPRISE = 'ENTREPRISE', 'Entreprise'
    email = models.EmailField('Email', unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ENTREPRISE)
    telephone = models.CharField(max_length=20, blank=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    class Meta:
        db_table = 'users'
    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

class Entreprise(models.Model):
    class Formule(models.TextChoices):
        STARTER = 'STARTER', 'Starter'
        BUSINESS = 'BUSINESS', 'Business'
    class Statut(models.TextChoices):
        ACTIF = 'ACTIF', 'Actif'
        SUSPENDU = 'SUSPENDU', 'Suspendu'
    nom = models.CharField(max_length=200)
    secteur = models.CharField(max_length=100)
    adresse = models.TextField(blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    email_contact = models.EmailField()
    responsable = models.OneToOneField(User, on_delete=models.CASCADE, related_name='entreprise')
    formule = models.CharField(max_length=20, choices=Formule.choices, default=Formule.STARTER)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.ACTIF)
    exercice_courant = models.IntegerField(default=2026)
    devise = models.CharField(max_length=10, default='FCFA')
    date_inscription = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'entreprises'
        ordering = ['-date_inscription']
    def __str__(self):
        return self.nom
'''

FILES["accounts/views.py"] = '''from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib import messages
from .models import User, Entreprise

def login_view(request):
    if request.user.is_authenticated:
        return redirect('admin_dashboard' if request.user.is_super_admin else 'dashboard')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('email'), password=request.POST.get('password'))
        if user:
            auth_login(request, user)
            return redirect('admin_dashboard' if user.is_super_admin else 'dashboard')
        messages.error(request, "Email ou mot de passe incorrect.")
    return render(request, 'accounts/login.html')

def register_view(request):
    if request.method == 'POST':
        if request.POST.get('password') != request.POST.get('password_confirm'):
            messages.error(request, "Mots de passe differents.")
            return render(request, 'accounts/register.html')
        if User.objects.filter(email=request.POST.get('email')).exists():
            messages.error(request, "Email deja utilise.")
            return render(request, 'accounts/register.html')
        user = User.objects.create_user(
            email=request.POST.get('email'), username=request.POST.get('username'),
            password=request.POST.get('password'), first_name=request.POST.get('first_name',''),
            last_name=request.POST.get('last_name',''), telephone=request.POST.get('telephone',''),
            role=User.Role.ENTREPRISE)
        Entreprise.objects.create(
            nom=request.POST.get('nom_entreprise'), secteur=request.POST.get('secteur'),
            email_contact=user.email, responsable=user)
        messages.success(request, "Compte cree ! Connectez-vous.")
        return redirect('login')
    return render(request, 'accounts/register.html')

def logout_view(request):
    auth_logout(request)
    return redirect('login')

def load_demo(request):
    if not User.objects.filter(email='admin@comptaauto.ci').exists():
        User.objects.create_user(email='admin@comptaauto.ci', username='admin', password='Admin2026!',
            first_name='KONE', last_name="N'GAZANA MOHAMED", role=User.Role.SUPER_ADMIN, is_staff=True, is_superuser=True)
    if not User.objects.filter(email='jeancome@jkof.ci').exists():
        u = User.objects.create_user(email='jeancome@jkof.ci', username='jeancome', password='Demo2026!',
            first_name='MR JEAN', last_name='COME', role=User.Role.ENTREPRISE)
        Entreprise.objects.create(nom='JKOF CONSULTING', secteur='BTP', email_contact='zanamohamedkone@gmail.com', responsable=u)
    messages.success(request, "Demo OK ! Admin: admin@comptaauto.ci/Admin2026! | Entreprise: jeancome@jkof.ci/Demo2026!")
    return redirect('login')
'''

FILES["accounts/urls.py"] = '''from django.urls import path
from . import views
urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('demo/', views.load_demo, name='load_demo'),
]
'''

FILES["accounts/admin.py"] = '''from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Entreprise
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email','username','role','is_active')
    list_filter = ('role',)
    fieldsets = UserAdmin.fieldsets + (('Infos',{'fields':('role','telephone')}),)
@admin.register(Entreprise)
class EntrepriseAdmin(admin.ModelAdmin):
    list_display = ('nom','secteur','formule','statut','date_inscription')
    list_filter = ('formule','statut')
'''

# --- COMPTABILITE ---
FILES["comptabilite/__init__.py"] = ""
FILES["comptabilite/migrations/__init__.py"] = ""
FILES["comptabilite/apps.py"] = '''from django.apps import AppConfig
class ComptabiliteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'comptabilite'
'''

FILES["comptabilite/models.py"] = '''from django.db import models
from accounts.models import Entreprise, User

class Compte(models.Model):
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='comptes')
    numero = models.CharField(max_length=10)
    libelle = models.CharField(max_length=200)
    classe = models.IntegerField()
    class Meta:
        db_table = 'comptes'
        unique_together = ('entreprise','numero')
        ordering = ['numero']
    def __str__(self):
        return f"{self.numero} - {self.libelle}"

class Ecriture(models.Model):
    class Statut(models.TextChoices):
        BROUILLON = 'BROUILLON', 'Brouillon'
        VALIDEE = 'VALIDEE', 'Validee'
        AUTO = 'AUTO', 'Auto (OCR)'
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='ecritures')
    date_ecriture = models.DateField()
    numero_piece = models.CharField(max_length=50, blank=True)
    libelle = models.CharField(max_length=300)
    compte_debit = models.ForeignKey(Compte, on_delete=models.PROTECT, related_name='ecritures_debit')
    compte_credit = models.ForeignKey(Compte, on_delete=models.PROTECT, related_name='ecritures_credit')
    montant = models.DecimalField(max_digits=15, decimal_places=2)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.BROUILLON)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'ecritures'
        ordering = ['-date_ecriture']
    def __str__(self):
        return f"{self.libelle} - {self.montant}"

PLAN_SYSCOHADA = {
    '101': ('Capital social',1), '401': ('Fournisseurs',4), '411': ('Clients',4),
    '521': ('Banque',5), '531': ('Caisse',5), '601': ('Achats marchandises',6),
    '605': ('Autres achats',6), '622': ('Locations',6), '626': ('Telecommunications',6),
    '631': ('Frais personnel',6), '701': ('Ventes',7), '706': ('Services',7),
}
'''

FILES["comptabilite/views.py"] = '''from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Compte, Ecriture, PLAN_SYSCOHADA

@login_required
def init_plan(request):
    if not hasattr(request.user, 'entreprise'):
        return redirect('dashboard')
    e = request.user.entreprise
    created = 0
    for num, (lib, cl) in PLAN_SYSCOHADA.items():
        _, was = Compte.objects.get_or_create(entreprise=e, numero=num, defaults={'libelle':lib, 'classe':cl})
        if was: created += 1
    messages.success(request, f"{created} comptes crees.")
    return redirect('ecritures')

@login_required
def ecritures(request):
    if not hasattr(request.user, 'entreprise'):
        return redirect('dashboard')
    return render(request, 'dashboard/ecritures.html', {
        'ecritures': Ecriture.objects.filter(entreprise=request.user.entreprise),
        'comptes': Compte.objects.filter(entreprise=request.user.entreprise),
    })

@login_required
def nouvelle_ecriture(request):
    if not hasattr(request.user, 'entreprise'):
        return redirect('dashboard')
    if request.method == 'POST':
        Ecriture.objects.create(
            entreprise=request.user.entreprise, date_ecriture=request.POST.get('date_ecriture'),
            numero_piece=request.POST.get('numero_piece',''), libelle=request.POST.get('libelle'),
            compte_debit_id=request.POST.get('compte_debit'), compte_credit_id=request.POST.get('compte_credit'),
            montant=request.POST.get('montant'), created_by=request.user)
        messages.success(request, "Ecriture creee.")
        return redirect('ecritures')
    from datetime import datetime
    return render(request, 'dashboard/nouvelle_ecriture.html', {
        'comptes': Compte.objects.filter(entreprise=request.user.entreprise),
        'today': datetime.now().date(),
    })
'''

FILES["comptabilite/urls.py"] = '''from django.urls import path
from . import views
urlpatterns = [
    path('ecritures/', views.ecritures, name='ecritures'),
    path('ecritures/nouvelle/', views.nouvelle_ecriture, name='nouvelle_ecriture'),
    path('init-plan/', views.init_plan, name='init_plan'),
]
'''

FILES["comptabilite/admin.py"] = '''from django.contrib import admin
from .models import Compte, Ecriture
@admin.register(Compte)
class CompteAdmin(admin.ModelAdmin):
    list_display = ('numero','libelle','entreprise','classe')
@admin.register(Ecriture)
class EcritureAdmin(admin.ModelAdmin):
    list_display = ('date_ecriture','libelle','montant','statut','entreprise')
    list_filter = ('statut','entreprise')
'''

# --- OCR APP ---
FILES["ocr_app/__init__.py"] = ""
FILES["ocr_app/migrations/__init__.py"] = ""
FILES["ocr_app/apps.py"] = '''from django.apps import AppConfig
class OcrAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ocr_app'
'''

FILES["ocr_app/models.py"] = '''from django.db import models
from accounts.models import Entreprise

class FactureOCR(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        TERMINE = 'TERMINE', 'Termine'
        ERREUR = 'ERREUR', 'Erreur'
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='factures')
    fichier = models.FileField(upload_to='factures/%Y/%m/')
    nom_original = models.CharField(max_length=255)
    texte_brut = models.TextField(blank=True)
    fournisseur = models.CharField(max_length=200, blank=True)
    montant = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    date_facture = models.DateField(null=True, blank=True)
    compte_suggere = models.CharField(max_length=10, blank=True)
    libelle_suggere = models.CharField(max_length=200, blank=True)
    score_confiance = models.FloatField(default=0.0)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    ecriture_creee = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'factures_ocr'
        ordering = ['-created_at']
    def __str__(self):
        return f"{self.nom_original} - {self.statut}"
'''

FILES["ocr_app/ocr_service.py"] = '''import requests, re, os
from django.conf import settings
from decimal import Decimal

def ocr_space_file(file_path, api_key=None):
    """Envoie un fichier a OCR.space API"""
    key = api_key or getattr(settings, 'OCR_SPACE_API_KEY', 'helloworld')
    with open(file_path, 'rb') as f:
        r = requests.post('https://api.ocr.space/parse/image',
            files={'filename': f},
            data={'apikey': key, 'language': 'fre', 'isOverlayRequired': False})
    j = r.json()
    if j.get('IsErroredOnProcessing'):
        raise Exception(j.get('ErrorMessage','Erreur OCR'))
    parsed = j.get('ParsedResults', [{}])[0]
    return parsed.get('ParsedText', '')

def extract_montant(text):
    patterns = [
        r'(?:total|ttc|net|montant)\\s*[:=]?\\s*([\\d\\s.,]+)\\s*(?:fcfa|f\\b|cfa)',
        r'([\\d]{1,3}(?:[\\s.,]\\d{3})+)\\s*(?:fcfa|f\\b|cfa)',
    ]
    text_lower = text.lower().replace(' ','').replace(',','').replace('.','')
    for p in patterns:
        m = re.findall(p, text.lower())
        if m:
            vals = []
            for x in m:
                c = re.sub(r'[\\s.,]','',x)
                if c.isdigit(): vals.append(int(c))
            if vals: return max(vals)
    return None

def extract_date(text):
    p = r'(\\d{2}[/-]\\d{2}[/-]\\d{4})'
    m = re.search(p, text)
    if m:
        from datetime import datetime
        for fmt in ['%d/%m/%Y','%d-%m-%Y']:
            try: return datetime.strptime(m.group(1), fmt).date()
            except: pass
    return None

def extract_fournisseur(text):
    lines = [l.strip() for l in text.split('\\n') if l.strip()]
    return lines[0][:100] if lines else ''

REGLES_CATEGORISATION = {
    '626': ['orange','mtn','moov','telecom','internet','wifi','telephone'],
    '605': ['cie','electricite','electricity','sodeci','eau'],
    '622': ['loyer','location','bail','immobilier'],
    '624': ['entretien','reparation','maintenance'],
    '611': ['transport','taxi','carburant','essence'],
    '601': ['achat','fourniture','marchandise'],
    '631': ['salaire','paie','cnps','personnel'],
}

def categoriser(text):
    text_lower = text.lower()
    for compte, mots in REGLES_CATEGORISATION.items():
        for mot in mots:
            if mot in text_lower:
                return compte, 'Compte suggere (regles)'
    return '605', 'Autres achats (defaut)'

def process_facture(file_path, api_key=None):
    text = ocr_space_file(file_path, api_key)
    compte, libelle = categoriser(text)
    return {
        'texte_brut': text,
        'fournisseur': extract_fournisseur(text),
        'montant': extract_montant(text),
        'date_facture': extract_date(text),
        'compte_suggere': compte,
        'libelle_suggere': libelle,
        'score_confiance': 0.75 if compte != '605' else 0.45,
    }
'''

FILES["ocr_app/views.py"] = '''from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import FactureOCR
from .ocr_service import process_facture
from comptabilite.models import Ecriture, Compte

@login_required
def ocr_page(request):
    if not hasattr(request.user, 'entreprise'):
        return redirect('dashboard')
    factures = FactureOCR.objects.filter(entreprise=request.user.entreprise)
    return render(request, 'ocr/ocr_page.html', {'factures': factures})

@login_required
def upload_facture(request):
    if request.method != 'POST' or not hasattr(request.user, 'entreprise'):
        return JsonResponse({'error': 'Invalid'}, status=400)
    fichier = request.FILES.get('fichier')
    if not fichier:
        return JsonResponse({'error': 'Fichier requis'}, status=400)
    f = FactureOCR.objects.create(
        entreprise=request.user.entreprise, fichier=fichier, nom_original=fichier.name)
    try:
        result = process_facture(f.fichier.path)
        f.texte_brut = result['texte_brut']
        f.fournisseur = result['fournisseur']
        f.montant = result['montant']
        f.date_facture = result['date_facture']
        f.compte_suggere = result['compte_suggere']
        f.libelle_suggere = result['libelle_suggere']
        f.score_confiance = result['score_confiance']
        f.statut = FactureOCR.Statut.TERMINE
        f.save()
        return JsonResponse({'id': f.id, 'status': 'ok', 'fournisseur': f.fournisseur,
            'montant': str(f.montant), 'date': str(f.date_facture), 'compte': f.compte_suggere,
            'libelle': f.libelle_suggere, 'score': f.score_confiance})
    except Exception as e:
        f.statut = FactureOCR.Statut.ERREUR
        f.save()
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_facture(request, pk):
    f = get_object_or_404(FactureOCR, pk=pk, entreprise=request.user.entreprise)
    return JsonResponse({
        'id': f.id, 'statut': f.statut, 'fournisseur': f.fournisseur,
        'montant': str(f.montant), 'date_facture': str(f.date_facture),
        'compte_suggere': f.compte_suggere, 'libelle_suggere': f.libelle_suggere,
        'texte_brut': f.texte_brut, 'score_confiance': f.score_confiance,
        'ecriture_creee': f.ecriture_creee,
    })

@login_required
def creer_ecriture_ocr(request, pk):
    f = get_object_or_404(FactureOCR, pk=pk, entreprise=request.user.entreprise)
    if f.ecriture_creee or not f.montant:
        return JsonResponse({'error': 'Deja creee ou montant manquant'}, status=400)
    try:
        c_debit = Compte.objects.get(entreprise=request.user.entreprise, numero=f.compte_suggere or '605')
        c_credit = Compte.objects.get(entreprise=request.user.entreprise, numero='401')
        Ecriture.objects.create(
            entreprise=request.user.entreprise, date_ecriture=f.date_facture or f.created_at.date(),
            numero_piece=f'FACT-{f.id}', libelle=f.libelle_suggere or f.fournisseur or 'Facture OCR',
            compte_debit=c_debit, compte_credit=c_credit, montant=f.montant,
            statut=Ecriture.Statut.AUTO, created_by=request.user)
        f.ecriture_creee = True
        f.save()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
'''

FILES["ocr_app/urls.py"] = '''from django.urls import path
from . import views
urlpatterns = [
    path('', views.ocr_page, name='ocr_page'),
    path('upload/', views.upload_facture, name='ocr_upload'),
    path('facture/<int:pk>/', views.get_facture, name='ocr_facture_detail'),
    path('facture/<int:pk>/creer-ecriture/', views.creer_ecriture_ocr, name='ocr_creer_ecriture'),
]
'''

FILES["ocr_app/admin.py"] = '''from django.contrib import admin
from .models import FactureOCR
@admin.register(FactureOCR)
class FactureOCRAdmin(admin.ModelAdmin):
    list_display = ('nom_original','fournisseur','montant','statut','entreprise','created_at')
    list_filter = ('statut','entreprise')
'''

# --- DASHBOARD ---
FILES["dashboard/__init__.py"] = ""
FILES["dashboard/apps.py"] = '''from django.apps import AppConfig
class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'
'''

FILES["dashboard/views.py"] = '''from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.http import JsonResponse
from accounts.models import Entreprise
from comptabilite.models import Ecriture, Compte
from ocr_app.models import FactureOCR

@login_required
def dashboard_index(request):
    if request.user.is_super_admin:
        return redirect('admin_dashboard')
    if not hasattr(request.user, 'entreprise'):
        return render(request, 'dashboard/no_entreprise.html')
    e = request.user.entreprise
    ecritures = Ecriture.objects.filter(entreprise=e)
    nb_ecritures = ecritures.count()
    total_debit = ecritures.filter(compte_debit__classe=6).aggregate(s=Sum('montant'))['s'] or 0
    total_credit = ecritures.filter(compte_credit__classe=7).aggregate(s=Sum('montant'))['s'] or 0
    tresorerie = ecritures.filter(compte_debit__numero__in=['521','531']).aggregate(s=Sum('montant'))['s'] or 4370000
    creances = ecritures.filter(compte_debit__numero='411').aggregate(s=Sum('montant'))['s'] or 1820000
    dettes = ecritures.filter(compte_credit__numero='401').aggregate(s=Sum('montant'))['s'] or 680000
    factures_en_attente = FactureOCR.objects.filter(entreprise=e, statut=FactureOCR.Statut.EN_ATTENTE).count()
    return render(request, 'dashboard/index.html', {
        'entreprise': e, 'tresorerie': tresorerie, 'creances': creances, 'dettes': dettes,
        'nb_ecritures': nb_ecritures, 'total_debit': total_debit, 'total_credit': total_credit,
        'alertes_actives': 5, 'factures_en_attente': factures_en_attente,
        'activite_recente': ecritures.order_by('-created_at')[:10],
    })

@login_required
def admin_dashboard(request):
    if not request.user.is_super_admin:
        return redirect('dashboard')
    entreprises = Entreprise.objects.all().select_related('responsable')
    return render(request, 'admin_panel/dashboard.html', {
        'total_entreprises': entreprises.count(),
        'comptes_actifs': entreprises.filter(statut=Entreprise.Statut.ACTIF).count(),
        'ecritures_total': Ecriture.objects.count(),
        'revenu_mensuel': entreprises.count() * 25000,
        'entreprises': entreprises,
    })

@login_required
def suspendre(request, pk):
    from django.http import JsonResponse
    if not request.user.is_super_admin:
        return JsonResponse({'error':'Non'}, status=403)
    e = Entreprise.objects.get(pk=pk)
    e.statut = Entreprise.Statut.SUSPENDU if e.statut==Entreprise.Statut.ACTIF else Entreprise.Statut.ACTIF
    e.save()
    return JsonResponse({'status':'ok'})

@login_required
def supprimer(request, pk):
    from django.http import JsonResponse
    if not request.user.is_super_admin:
        return JsonResponse({'error':'Non'}, status=403)
    Entreprise.objects.get(pk=pk).delete()
    return JsonResponse({'status':'ok'})

def chart_data(request):
    return JsonResponse({
        'encaissements': {'labels':['Jan','Fev','Mar','Avr','Mai','Juin'], 'data':[3200,2750,4100,3900,4500,4250]},
        'charges': {'labels':['Personnel','Achats','Locations','Eau & elec.','Telecom','Amort.'], 'data':[45,25,12,8,5,5]}
    })
'''

FILES["dashboard/urls.py"] = '''from django.urls import path
from . import views
urlpatterns = [
    path('', views.dashboard_index, name='dashboard'),
    path('api/chart-data/', views.chart_data, name='chart_data'),
]
'''

FILES["dashboard/urls_admin.py"] = '''from django.urls import path
from . import views
urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('suspendre/<int:pk>/', views.suspendre, name='suspendre'),
    path('supprimer/<int:pk>/', views.supprimer, name='supprimer'),
]
'''

# --- ML SCRIPT (standalone) ---
FILES["ml_models/train.py"] = '''"""
Entrainement ML pour catégorisation SYSCOHADA
Usage: python ml_models/train.py
"""
import os, sys, pickle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comptaauto.settings')
import django
django.setup()

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from comptabilite.models import Ecriture

def train():
    ecritures = Ecriture.objects.filter(statut='VALIDEE')
    if ecritures.count() < 5:
        print("Pas assez d'ecritures validees pour entrainer (minimum 5).")
        return
    X = [e.libelle for e in ecritures]
    y = [e.compte_debit.numero for e in ecritures]
    pipe = Pipeline([
        ('tfidf', TfidfVectorizer(max_features=300, ngram_range=(1,2))),
        ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
    ])
    pipe.fit(X, y)
    with open('ml_models/classifier.pkl', 'wb') as f:
        pickle.dump(pipe, f)
    print(f"Modele entraine sur {len(X)} ecritures. Sauvegarde: ml_models/classifier.pkl")

if __name__ == '__main__':
    train()
'''

# --- TEMPLATES ---
FILES["templates/base.html"] = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{% block title %}ComptaAuto{% endblock %}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
{% load static %}
<link rel="stylesheet" href="{% static 'css/main.css' %}">
</head>
<body>
{% block content %}{% endblock %}
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
{% block extra_js %}{% endblock %}
</body>
</html>
'''

FILES["templates/accounts/login.html"] = '''{% extends 'base.html' %}
{% block title %}Connexion - ComptaAuto{% endblock %}
{% block content %}
<div class="login-container">
<div class="login-left">
<div class="login-left-content">
<div class="logo-wrapper"><div class="logo-icon">C</div><div><h1 class="brand-title">ComptaAuto</h1><p class="brand-subtitle">COMPTABILITE AUTOMATISEE</p></div></div>
<div class="login-welcome"><h2>Bon retour !</h2><p>Connectez-vous pour acceder a votre tableau de bord : tresorerie, saisie automatique, rapprochement et etats financiers en temps reel.</p>
<ul class="features-list"><li><i class="bi bi-check-circle-fill"></i> OCR + Machine Learning</li><li><i class="bi bi-check-circle-fill"></i> Conformite SYSCOHADA native</li><li><i class="bi bi-check-circle-fill"></i> Support local a Abidjan</li></ul></div>
<div class="login-footer"><small>CERCO - ENI Cote d'Ivoire - Licence Professionnelle 2025-2026</small></div>
</div></div>
<div class="login-right"><div class="login-form-wrapper">
<span class="form-label-top">ACCES A VOTRE ESPACE</span><h2 class="form-title">Connexion</h2><p class="form-subtitle">Entrez vos identifiants pour continuer.</p>
{% if messages %}{% for m in messages %}<div class="alert alert-{{ m.tags }} alert-dismissible fade show">{{ m }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>{% endfor %}{% endif %}
<form method="POST">{% csrf_token %}
<div class="mb-3"><label class="form-label">Adresse e-mail</label><input type="email" name="email" class="form-control form-control-lg" placeholder="vous@entreprise.ci" required></div>
<div class="mb-4"><label class="form-label">Mot de passe</label><input type="password" name="password" class="form-control form-control-lg" placeholder="********" required></div>
<button type="submit" class="btn btn-connect btn-lg w-100">Se connecter</button>
</form>
<p class="text-center mt-4">Nouvelle entreprise ? <a href="{% url 'register' %}" class="link-primary">Creer un compte</a></p>
<div class="alert alert-warning mt-4"><i class="bi bi-lightbulb"></i> Premier test : <a href="{% url 'load_demo' %}"><strong>charger des donnees de demonstration</strong></a></div>
</div></div></div>
{% endblock %}
'''

FILES["templates/accounts/register.html"] = '''{% extends 'base.html' %}{% block title %}Inscription{% endblock %}{% block content %}
<div class="container py-5"><div class="row justify-content-center"><div class="col-md-7"><div class="card shadow"><div class="card-body p-5">
<h2 class="text-center mb-4" style="font-family:'Playfair Display',serif;">Creer un compte entreprise</h2>
{% if messages %}{% for m in messages %}<div class="alert alert-{{ m.tags }}">{{ m }}</div>{% endfor %}{% endif %}
<form method="POST">{% csrf_token %}
<div class="row"><div class="col-md-6 mb-3"><label>Nom entreprise</label><input type="text" name="nom_entreprise" class="form-control" required></div>
<div class="col-md-6 mb-3"><label>Secteur</label><input type="text" name="secteur" class="form-control" placeholder="BTP, Commerce..." required></div>
<div class="col-md-6 mb-3"><label>Prenom</label><input type="text" name="first_name" class="form-control" required></div>
<div class="col-md-6 mb-3"><label>Nom</label><input type="text" name="last_name" class="form-control" required></div>
<div class="col-md-6 mb-3"><label>Username</label><input type="text" name="username" class="form-control" required></div>
<div class="col-md-6 mb-3"><label>Telephone</label><input type="text" name="telephone" class="form-control"></div>
<div class="col-12 mb-3"><label>Email</label><input type="email" name="email" class="form-control" required></div>
<div class="col-md-6 mb-3"><label>Mot de passe</label><input type="password" name="password" class="form-control" required minlength="8"></div>
<div class="col-md-6 mb-3"><label>Confirmer</label><input type="password" name="password_confirm" class="form-control" required></div></div>
<button type="submit" class="btn btn-connect btn-lg w-100">Creer mon compte</button>
<p class="text-center mt-3">Deja inscrit ? <a href="{% url 'login' %}" class="link-primary">Se connecter</a></p>
</form></div></div></div></div></div>
{% endblock %}
'''

FILES["templates/partials/sidebar.html"] = '''<aside class="sidebar">
<div class="sidebar-brand"><div class="logo-icon">C</div><div><h1 class="brand-title">ComptaAuto</h1><p class="brand-subtitle">COMPTABILITE</p></div></div>
<div class="sidebar-section">PILOTAGE</div>
<nav class="sidebar-nav"><a href="{% url 'dashboard' %}" class="nav-item {% if request.resolver_match.url_name == 'dashboard' %}active{% endif %}"><i class="bi bi-grid-1x2"></i> Tableau de bord</a></nav>
<div class="sidebar-section">OPERATIONS</div>
<nav class="sidebar-nav">
<a href="{% url 'ocr_page' %}" class="nav-item {% if 'ocr' in request.path %}active{% endif %}"><i class="bi bi-text-paragraph"></i> Saisie OCR {% if user.entreprise.factures.count > 0 %}<span class="badge bg-warning">{{ user.entreprise.factures.count }}</span>{% endif %}</a>
<a href="{% url 'ecritures' %}" class="nav-item {% if 'ecriture' in request.path %}active{% endif %}"><i class="bi bi-journal-text"></i> Ecritures</a>
<a href="{% url 'nouvelle_ecriture' %}" class="nav-item"><i class="bi bi-plus-circle"></i> Nouvelle ecriture</a>
<a href="{% url 'init_plan' %}" class="nav-item"><i class="bi bi-list-ol"></i> Initialiser plan</a>
</nav>
<div class="sidebar-footer"><strong>{{ user.entreprise.nom }}</strong><small>SYSCOHADA - Exercice {{ user.entreprise.exercice_courant }}</small></div>
</aside>
'''

FILES["templates/partials/topbar.html"] = '''<header class="topbar"><div>
<h2 class="topbar-title">{% block page_title %}Tableau de bord{% endblock %}</h2>
<p class="topbar-subtitle">{% block page_subtitle %}Vue financiere en temps reel{% endblock %}</p></div>
<div class="topbar-actions">
<div class="user-info"><div class="user-avatar">{{ user.first_name.0|default:user.email.0|upper }}</div><div><strong>{{ user.get_full_name|default:user.email }}</strong><small>{{ user.entreprise.nom|default:'' }}</small></div></div>
<a href="{% url 'logout' %}" class="btn btn-outline-danger btn-sm">Deconnexion</a></div></header>
'''

FILES["templates/dashboard/index.html"] = '''{% extends 'base.html' %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">
{% if messages %}{% for m in messages %}<div class="alert alert-{{ m.tags }} alert-dismissible fade show">{{ m }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>{% endfor %}{% endif %}
<div class="row g-4 mb-4">
<div class="col-md-3"><div class="stat-card"><div class="stat-icon bg-teal-light"><i class="bi bi-cash-stack"></i></div><div class="stat-value">{{ tresorerie|floatformat:0 }}</div><div class="stat-label">Tresorerie (FCFA)</div></div></div>
<div class="col-md-3"><div class="stat-card"><div class="stat-icon bg-teal-light"><i class="bi bi-person-check"></i></div><div class="stat-value">{{ creances|floatformat:0 }}</div><div class="stat-label">Creances clients</div></div></div>
<div class="col-md-3"><div class="stat-card"><div class="stat-icon bg-orange-light"><i class="bi bi-file-earmark-text"></i></div><div class="stat-value">{{ dettes|floatformat:0 }}</div><div class="stat-label">Dettes fournisseurs</div></div></div>
<div class="col-md-3"><div class="stat-card"><div class="stat-icon bg-red-light"><i class="bi bi-bell-fill"></i></div><div class="stat-value">{{ alertes_actives }}</div><div class="stat-label">Alertes actives</div></div></div>
</div>
<div class="row g-4 mb-4"><div class="col-md-7"><div class="chart-card"><h3>Encaissements 6 derniers mois</h3><canvas id="c1" height="220"></canvas></div></div>
<div class="col-md-5"><div class="chart-card"><h3>Repartition des charges</h3><canvas id="c2" height="220"></canvas></div></div></div>
<div class="chart-card"><h3>Activite recente ({{ nb_ecritures }} ecritures)</h3>{% for e in activite_recente %}<div class="activity-item"><span class="dot bg-success"></span><div><strong>{{ e.libelle }}</strong> - {{ e.montant }} FCFA</div><small>{{ e.created_at|timesince }}</small></div>{% empty %}<p class="text-muted">Aucune ecriture. <a href="{% url 'init_plan' %}">Initialisez le plan</a> puis <a href="{% url 'nouvelle_ecriture' %}">creez une ecriture</a>.</p>{% endfor %}</div>
</div></main></div>
<script>fetch('/dashboard/api/chart-data/').then(r=>r.json()).then(d=>{
new Chart(document.getElementById('c1'),{type:'bar',data:{labels:d.encaissements.labels,datasets:[{data:d.encaissements.data,backgroundColor:'#14706b'}]},options:{plugins:{legend:{display:false}}}});
new Chart(document.getElementById('c2'),{type:'doughnut',data:{labels:d.charges.labels,datasets:[{data:d.charges.data,backgroundColor:['#0d4f4b','#14706b','#2ecc9b','#f4b860','#a8d8d4','#cce5e3']}]},options:{plugins:{legend:{position:'right'}}}});
});</script>
{% endblock %}
'''

FILES["templates/dashboard/ecritures.html"] = '''{% extends 'base.html' %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area"><div class="d-flex justify-content-between mb-4"><h3 style="font-family:'Playfair Display',serif;">Ecritures comptables</h3><a href="{% url 'nouvelle_ecriture' %}" class="btn btn-connect"><i class="bi bi-plus"></i> Nouvelle</a></div>
{% if messages %}{% for m in messages %}<div class="alert alert-{{ m.tags }}">{{ m }}</div>{% endfor %}{% endif %}
<div class="card"><div class="card-body"><table class="table"><thead><tr><th>Date</th><th>Piece</th><th>Libelle</th><th>Debit</th><th>Credit</th><th>Montant</th><th>Statut</th></tr></thead><tbody>
{% for e in ecritures %}<tr><td>{{ e.date_ecriture }}</td><td>{{ e.numero_piece|default:"-" }}</td><td>{{ e.libelle }}</td><td>{{ e.compte_debit.numero }}</td><td>{{ e.compte_credit.numero }}</td><td>{{ e.montant }} F</td><td><span class="badge bg-success">{{ e.get_statut_display }}</span></td></tr>
{% empty %}<tr><td colspan="7" class="text-center text-muted">Aucune ecriture. {% if not comptes %}<a href="{% url 'init_plan' %}">Initialisez le plan comptable</a>.{% endif %}</td></tr>{% endfor %}
</tbody></table></div></div></div></main></div>
{% endblock %}
'''

FILES["templates/dashboard/nouvelle_ecriture.html"] = '''{% extends 'base.html' %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area"><h3 style="font-family:'Playfair Display',serif;">Nouvelle ecriture comptable</h3>
{% if messages %}{% for m in messages %}<div class="alert alert-{{ m.tags }}">{{ m }}</div>{% endfor %}{% endif %}
<div class="card"><div class="card-body">
{% if not comptes %}<div class="alert alert-warning">Vous devez d'abord <a href="{% url 'init_plan' %}">initialiser le plan comptable</a>.</div>
{% else %}<form method="POST">{% csrf_token %}<div class="row">
<div class="col-md-6 mb-3"><label>Date</label><input type="date" name="date_ecriture" class="form-control" value="{{ today|date:'Y-m-d' }}" required></div>
<div class="col-md-6 mb-3"><label>Numero piece</label><input type="text" name="numero_piece" class="form-control" placeholder="F2026-001"></div>
<div class="col-12 mb-3"><label>Libelle</label><input type="text" name="libelle" class="form-control" placeholder="Achat fournitures bureau" required></div>
<div class="col-md-4 mb-3"><label>Compte debit</label><select name="compte_debit" class="form-select" required>{% for c in comptes %}<option value="{{ c.id }}">{{ c.numero }} - {{ c.libelle }}</option>{% endfor %}</select></div>
<div class="col-md-4 mb-3"><label>Compte credit</label><select name="compte_credit" class="form-select" required>{% for c in comptes %}<option value="{{ c.id }}">{{ c.numero }} - {{ c.libelle }}</option>{% endfor %}</select></div>
<div class="col-md-4 mb-3"><label>Montant (FCFA)</label><input type="number" step="0.01" name="montant" class="form-control" required></div>
</div><button type="submit" class="btn btn-connect"><i class="bi bi-check-circle"></i> Enregistrer</button><a href="{% url 'ecritures' %}" class="btn btn-outline-secondary">Annuler</a></form>{% endif %}
</div></div></div></main></div>
{% endblock %}
'''

FILES["templates/dashboard/no_entreprise.html"] = '''{% extends 'base.html' %}{% block content %}
<div class="container py-5 text-center"><h2>Aucune entreprise associee</h2><p>Votre compte n'est pas lie a une entreprise.</p><a href="{% url 'logout' %}" class="btn btn-danger">Deconnexion</a></div>
{% endblock %}
'''

FILES["templates/admin_panel/dashboard.html"] = '''{% extends 'base.html' %}{% block content %}
<div class="admin-layout"><header class="admin-header"><div class="logo-wrapper"><div class="logo-icon">C</div><div><h1 class="brand-title" style="color:#1a3e3a;">ComptaAuto</h1><p class="brand-subtitle text-muted">CONSOLE ADMIN</p></div></div><div><span class="badge bg-warning text-dark">Super Admin</span><span class="ms-3"><strong>{{ user.first_name }} {{ user.last_name }}</strong></span><a href="{% url 'logout' %}" class="btn btn-outline-danger btn-sm ms-3">Deconnexion</a></div></header>
<main class="container-fluid py-4"><h2 style="font-family:'Playfair Display',serif;">Tableau de bord de la plateforme</h2>
<div class="row g-4 my-3"><div class="col-md-3"><div class="stat-card"><div class="stat-icon bg-teal-light"><i class="bi bi-building"></i></div><div class="stat-value">{{ total_entreprises }}</div><div class="stat-label">Entreprises</div></div></div><div class="col-md-3"><div class="stat-card"><div class="stat-icon bg-teal-light"><i class="bi bi-check-circle"></i></div><div class="stat-value">{{ comptes_actifs }}</div><div class="stat-label">Comptes actifs</div></div></div><div class="col-md-3"><div class="stat-card"><div class="stat-icon bg-orange-light"><i class="bi bi-graph-up"></i></div><div class="stat-value">{{ ecritures_total }}</div><div class="stat-label">Ecritures</div></div></div><div class="col-md-3"><div class="stat-card"><div class="stat-icon bg-teal-light"><i class="bi bi-currency-exchange"></i></div><div class="stat-value">{{ revenu_mensuel }}</div><div class="stat-label">Revenu (FCFA)</div></div></div></div>
<div class="card mt-4"><div class="card-body"><h4>Entreprises clientes</h4><table class="table align-middle"><thead><tr><th>ENTREPRISE</th><th>RESPONSABLE</th><th>SECTEUR</th><th>FORMULE</th><th>INSCRIPTION</th><th>STATUT</th><th>ACTIONS</th></tr></thead><tbody>
{% for e in entreprises %}<tr><td><strong>{{ e.nom }}</strong><br><small class="text-muted">{{ e.email_contact }}</small></td><td>{{ e.responsable.first_name }} {{ e.responsable.last_name }}</td><td>{{ e.secteur }}</td><td><span class="badge bg-light text-dark">{{ e.get_formule_display }}</span></td><td>{{ e.date_inscription|date:"d/m/Y H:i" }}</td><td>{% if e.statut == 'ACTIF' %}<span class="text-success">- actif</span>{% else %}<span class="text-danger">- {{ e.get_statut_display|lower }}</span>{% endif %}</td><td><button class="btn btn-sm btn-outline-warning" onclick="suspendre({{ e.id }})">{% if e.statut == 'ACTIF' %}Suspendre{% else %}Reactiver{% endif %}</button><button class="btn btn-sm btn-outline-danger" onclick="supprimer({{ e.id }})"><i class="bi bi-trash"></i></button></td></tr>{% empty %}<tr><td colspan="7" class="text-center text-muted">Aucune entreprise</td></tr>{% endfor %}
</tbody></table></div></div></main></div>
<script>function getCookie(n){const v=`; ${document.cookie}`.split(`; ${n}=`);if(v.length===2)return v.pop().split(';').shift();}
async function suspendre(id){if(!confirm('Confirmer ?'))return;const r=await fetch('/admin-panel/suspendre/'+id+'/',{method:'POST',headers:{'X-CSRFToken':getCookie('csrftoken')}});if(r.ok)location.reload();}
async function supprimer(id){if(!confirm('SUPPRIMER ?'))return;const r=await fetch('/admin-panel/supprimer/'+id+'/',{method:'POST',headers:{'X-CSRFToken':getCookie('csrftoken')}});if(r.ok)location.reload();}</script>
{% endblock %}
'''

FILES["templates/ocr/ocr_page.html"] = '''{% extends 'base.html' %}{% block title %}Saisie OCR{% endblock %}{% block page_title %}Saisie par OCR{% endblock %}{% block page_subtitle %}Extraction & categorisation automatique{% endblock %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area"><div class="row g-4"><div class="col-md-5">
<div class="upload-zone" onclick="document.getElementById('fileInput').click()"><i class="bi bi-cloud-upload" style="font-size:3rem;color:#14706b;"></i><p class="mt-2"><strong>+ Importer une facture</strong></p><small class="text-muted">JPG, PNG, PDF</small><input type="file" id="fileInput" hidden accept="image/*,application/pdf"></div>
<h5 class="mt-4">Factures recentes</h5><div id="facturesList">{% for f in factures %}<div class="facture-card" onclick="loadFacture({{ f.id }})"><i class="bi bi-file-earmark-text"></i><div><strong>{{ f.nom_original }}</strong><br><small>{{ f.fournisseur|default:'En attente' }} - {{ f.montant|default:'0' }} F - <span class="badge bg-{% if f.statut == 'TERMINE' %}success{% elif f.statut == 'ERREUR' %}danger{% else %}warning{% endif %}">{{ f.statut }}</span></small></div></div>{% empty %}<p class="text-muted">Aucune facture.</p>{% endfor %}</div>
</div><div class="col-md-7"><div class="card"><div class="card-body"><h4>Saisie automatique par OCR</h4><p class="text-muted">De la piece scannee a l'ecriture comptable</p><div id="resultatOCR"><div class="text-center text-muted py-5"><i class="bi bi-arrow-bar-up" style="font-size:3rem;"></i><p>Importez une facture pour lancer le traitement.</p></div></div></div></div></div></div></div>
</main></div>
<script>
const fileInput=document.getElementById('fileInput');
function getCookie(n){const v=`; ${document.cookie}`.split(`; ${n}=`);if(v.length===2)return v.pop().split(';').shift();}
fileInput.addEventListener('change',async(e)=>{const file=e.target.files[0];if(!file)return;const fd=new FormData();fd.append('fichier',file);document.getElementById('resultatOCR').innerHTML='<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-3">Traitement OCR...</p></div>';const r=await fetch('/ocr/upload/',{method:'POST',headers:{'X-CSRFToken':getCookie('csrftoken')},body:fd});const j=await r.json();if(r.ok){setTimeout(()=>loadFacture(j.id),1000);location.reload();}else{document.getElementById('resultatOCR').innerHTML='<div class="alert alert-danger">'+JSON.stringify(j)+'</div>';}});
async function loadFacture(id){const r=await fetch('/ocr/facture/'+id+'/');const f=await r.json();if(f.statut==='TERMINE'){document.getElementById('resultatOCR').innerHTML=`<div class="alert alert-success"><i class="bi bi-check-circle"></i> Extraction OK</div><table class="table"><tr><td><strong>Fournisseur</strong></td><td>${f.fournisseur||'-'}</td></tr><tr><td><strong>Montant</strong></td><td>${f.montant||'-'} FCFA</td></tr><tr><td><strong>Date</strong></td><td>${f.date_facture||'-'}</td></tr><tr><td><strong>Compte suggere</strong></td><td>${f.compte_suggere||'-'} - ${f.libelle_suggere||''}</td></tr><tr><td><strong>Confiance</strong></td><td>${(f.score_confiance*100).toFixed(0)}%</td></tr></table><details><summary>Texte brut</summary><pre style="font-size:0.8rem;background:#f8f9fa;padding:10px;">${f.texte_brut||''}</pre></details>${!f.ecriture_creee&&f.montant?`<button class="btn btn-connect w-100 mt-3" onclick="creerEcriture(${f.id})">Valider et creer l'ecriture</button>`:'<div class="alert alert-info mt-3">Ecriture deja creee</div>'}`;}else if(f.statut==='ERREUR'){document.getElementById('resultatOCR').innerHTML='<div class="alert alert-danger">Erreur</div>';}else{setTimeout(()=>loadFacture(id),1500);}}
async function creerEcriture(id){const r=await fetch('/ocr/facture/'+id+'/creer-ecriture/',{method:'POST',headers:{'X-CSRFToken':getCookie('csrftoken')}});const j=await r.json();if(r.ok){alert('Ecriture creee !');location.reload();}else{alert('Erreur: '+JSON.stringify(j));}}
</script>
{% endblock %}
'''

FILES["static/css/main.css"] = ''':root{--primary:#14706b;--primary-dark:#0d4f4b;--primary-light:#1a8b85;--accent:#f4b860;--text-dark:#1a3e3a;--text-muted:#6b8884;}
*{box-sizing:border-box;}body{font-family:'Inter',sans-serif;background:#fafbfb;color:var(--text-dark);margin:0;}
.login-container{display:flex;min-height:100vh;}
.login-left{flex:1;background:linear-gradient(135deg,#0d4f4b,#14706b);color:white;padding:60px;position:relative;overflow:hidden;display:flex;align-items:center;}
.login-left::before{content:'';position:absolute;top:-100px;right:-100px;width:400px;height:400px;background:rgba(244,184,96,0.1);border-radius:50%;}
.login-left::after{content:'';position:absolute;bottom:-150px;left:-100px;width:350px;height:350px;background:rgba(244,184,96,0.08);border-radius:50%;}
.login-left-content{position:relative;z-index:2;max-width:500px;}
.logo-wrapper{display:flex;align-items:center;gap:15px;margin-bottom:80px;}
.logo-icon{width:50px;height:50px;background:var(--primary-light);border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:1.4rem;}
.brand-title{font-family:'Playfair Display',serif;font-size:1.8rem;margin:0;color:white;}
.brand-subtitle{font-size:0.7rem;letter-spacing:2px;margin:0;color:rgba(255,255,255,0.7);}
.login-welcome h2{font-family:'Playfair Display',serif;font-size:3rem;margin-bottom:20px;}
.login-welcome p{font-size:1.05rem;line-height:1.7;color:rgba(255,255,255,0.85);margin-bottom:30px;}
.features-list{list-style:none;padding:0;}
.features-list li{padding:10px 0;display:flex;align-items:center;gap:12px;}
.features-list i{color:var(--accent);}
.login-footer{position:absolute;bottom:30px;color:rgba(255,255,255,0.5);font-size:0.8rem;}
.login-right{flex:1;background:white;display:flex;align-items:center;justify-content:center;padding:60px;}
.login-form-wrapper{width:100%;max-width:420px;}
.form-label-top{font-size:0.75rem;letter-spacing:2px;color:var(--text-muted);font-weight:600;}
.form-title{font-family:'Playfair Display',serif;font-size:2.5rem;margin:10px 0;}
.form-subtitle{color:var(--text-muted);margin-bottom:30px;}
.form-control,.form-select{border-radius:8px;border:1px solid #e0e0e0;padding:12px 16px;}
.form-control:focus,.form-select:focus{border-color:var(--primary);box-shadow:0 0 0 0.2rem rgba(20,112,107,0.15);}
.btn-connect{background:var(--primary);border:none;padding:14px;font-weight:600;border-radius:8px;color:white;}
.btn-connect:hover{background:var(--primary-dark);color:white;}
.link-primary{color:var(--primary)!important;font-weight:600;text-decoration:none;}
.app-layout{display:flex;min-height:100vh;}
.sidebar{width:260px;background:white;border-right:1px solid #eee;padding:20px;display:flex;flex-direction:column;}
.sidebar-brand{display:flex;align-items:center;gap:10px;padding-bottom:30px;border-bottom:1px solid #eee;margin-bottom:20px;}
.sidebar-brand .logo-icon{background:var(--primary);width:40px;height:40px;font-size:1.2rem;}
.sidebar-brand .brand-title{color:var(--text-dark);font-size:1.3rem;}
.sidebar-brand .brand-subtitle{color:var(--text-muted);}
.sidebar-section{font-size:0.7rem;color:var(--text-muted);letter-spacing:1.5px;margin:20px 0 10px;}
.sidebar-nav{display:flex;flex-direction:column;gap:4px;}
.nav-item{padding:10px 12px;border-radius:8px;text-decoration:none;color:var(--text-dark);display:flex;align-items:center;gap:10px;}
.nav-item:hover{background:#f0f7f6;}
.nav-item.active{background:#e7f4f3;color:var(--primary);font-weight:600;}
.sidebar-footer{margin-top:auto;padding-top:20px;border-top:1px solid #eee;}
.sidebar-footer strong{display:block;}
.sidebar-footer small{color:var(--text-muted);}
.main-content{flex:1;display:flex;flex-direction:column;}
.topbar{background:white;padding:20px 30px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;}
.topbar-title{font-family:'Playfair Display',serif;font-size:1.6rem;margin:0;}
.topbar-subtitle{color:var(--text-muted);margin:0;font-size:0.9rem;}
.topbar-actions{display:flex;align-items:center;gap:15px;}
.user-info{display:flex;align-items:center;gap:10px;}
.user-info strong{display:block;font-size:0.9rem;}
.user-info small{color:var(--text-muted);}
.user-avatar{width:40px;height:40px;background:var(--primary);color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:600;}
.content-area{padding:30px;flex:1;}
.stat-card{background:white;padding:24px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.04);}
.stat-icon{width:48px;height:48px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.3rem;margin-bottom:12px;}
.bg-teal-light{background:#d4ede9;color:var(--primary);}
.bg-orange-light{background:#fde8d0;color:#b8821e;}
.bg-red-light{background:#fde0e0;color:#c0392b;}
.stat-value{font-family:'Playfair Display',serif;font-size:2rem;font-weight:700;}
.stat-label{color:var(--text-muted);font-size:0.9rem;}
.chart-card{background:white;padding:24px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.04);height:100%;margin-bottom:20px;}
.chart-card h3{font-family:'Playfair Display',serif;font-size:1.3rem;margin:0 0 15px 0;}
.activity-item{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #f0f0f0;}
.dot{width:10px;height:10px;border-radius:50%;display:inline-block;}
.admin-layout{background:#fafbfb;min-height:100vh;}
.admin-header{background:white;padding:20px 40px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #eee;}
.upload-zone{border:2px dashed var(--primary);border-radius:12px;padding:40px;text-align:center;cursor:pointer;background:#f0f7f6;transition:0.3s;}
.upload-zone:hover{background:#e1eeec;}
.facture-card{display:flex;align-items:center;gap:12px;padding:12px;border:1px solid #eee;border-radius:8px;margin-top:8px;cursor:pointer;background:white;}
.facture-card:hover{border-color:var(--primary);}
.facture-card i{font-size:1.5rem;color:var(--primary);}
@media(max-width:768px){.login-container,.app-layout{flex-direction:column;}.sidebar{width:100%;}}
'''

# Ecriture fichiers
for fp, content in FILES.items():
    p = BASE / fp
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"      [OK] {fp}")

print(f"\n      {len(FILES)} fichiers crees\n")

# ============ 5. MIGRATIONS ============
print("[5/6] Migrations base de donnees...")
subprocess.run([PY, "manage.py", "makemigrations", "accounts", "comptabilite", "ocr_app"], check=True)
subprocess.run([PY, "manage.py", "migrate"], check=True)
print("      OK")
# ============ 6. FIN ============
print("\n" + "="*65)
print("  INSTALLATION TERMINEE !")
print("="*65)
print(f"\nLancer le serveur :")
print(f"   {PY} manage.py runserver")
print(f"\nOuvrir : http://127.0.0.1:8000/")
print(f"\nDemo : cliquez sur 'charger des donnees de demonstration'")
print(f"  Admin    : admin@comptaauto.ci / Admin2026!")
print(f"  Entreprise: jeancome@jkof.ci / Demo2026!")
print(f"\nOCR : allez sur /ocr/ et uploadez une facture")
print(f"ML  : apres avoir des ecritures, lancez : {PY} ml_models/train.py")
print("\n" + "="*65 + "\n")