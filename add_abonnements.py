"""
COMPTAAUTO - Systeme d'abonnement complet
- 5 forfaits : Freemium, Starter, Pro, Enterprise, Annuel
- Decompte jours restants
- Blocage si expire
- Paiements + factures PDF
- Notifications expiration
Usage: python add_abonnements.py
"""
import os, sys, subprocess
from pathlib import Path

BASE = Path(__file__).parent

print("\n" + "="*65)
print("  AJOUT SYSTEME D'ABONNEMENT")
print("="*65 + "\n")

if os.name == 'nt':
    PY = str(BASE / "venv" / "Scripts" / "python.exe")
    PIP = str(BASE / "venv" / "Scripts" / "pip.exe")
else:
    PY = str(BASE / "venv" / "bin" / "python")
    PIP = str(BASE / "venv" / "bin" / "pip")

print("[1/3] Creation dossiers...")
for d in ["abonnements", "abonnements/migrations", "templates/abonnements"]:
    (BASE / d).mkdir(parents=True, exist_ok=True)
print("      OK\n")

print("[2/3] Generation fichiers...")
FILES = {}

# ============================================
# APP ABONNEMENTS
# ============================================
FILES["abonnements/__init__.py"] = ""
FILES["abonnements/migrations/__init__.py"] = ""

FILES["abonnements/apps.py"] = '''from django.apps import AppConfig
class AbonnementsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'abonnements'
'''

FILES["abonnements/models.py"] = '''from django.db import models
from django.utils import timezone
from datetime import timedelta
from accounts.models import Entreprise, User


class Forfait(models.Model):
    """Forfaits disponibles"""
    CODES = [
        ('FREEMIUM', 'Freemium (Essai)'),
        ('STARTER', 'Starter'),
        ('PRO', 'Pro'),
        ('ENTERPRISE', 'Enterprise'),
        ('ANNUEL', 'Annuel'),
    ]

    code = models.CharField(max_length=20, choices=CODES, unique=True)
    nom = models.CharField(max_length=100)
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    duree_jours = models.IntegerField()
    description = models.TextField(blank=True)

    # Limites
    max_factures_ocr_mois = models.IntegerField(default=10)
    max_utilisateurs = models.IntegerField(default=1)
    max_ecritures_mois = models.IntegerField(default=50)
    rapprochement_bancaire = models.BooleanField(default=False)
    reporting_avance = models.BooleanField(default=False)
    support_prioritaire = models.BooleanField(default=False)
    export_illimite = models.BooleanField(default=False)

    # Affichage
    couleur = models.CharField(max_length=20, default='#14706b')
    icone = models.CharField(max_length=50, default='bi-star')
    populaire = models.BooleanField(default=False)
    actif = models.BooleanField(default=True)
    ordre = models.IntegerField(default=0)

    class Meta:
        db_table = 'forfaits'
        ordering = ['ordre', 'prix']

    def __str__(self):
        return f"{self.nom} ({self.prix} FCFA)"

    @property
    def prix_par_jour(self):
        return self.prix / self.duree_jours if self.duree_jours else 0


class Abonnement(models.Model):
    """Abonnement actif d'une entreprise"""
    STATUTS = [
        ('ACTIF', 'Actif'),
        ('EXPIRE', 'Expire'),
        ('SUSPENDU', 'Suspendu'),
        ('ANNULE', 'Annule'),
    ]

    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='abonnements')
    forfait = models.ForeignKey(Forfait, on_delete=models.PROTECT)
    date_debut = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField()
    statut = models.CharField(max_length=20, choices=STATUTS, default='ACTIF')
    auto_renouvellement = models.BooleanField(default=False)
    renouvelle_de = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    # Compteurs d'usage du mois
    factures_ocr_utilisees = models.IntegerField(default=0)
    ecritures_utilisees = models.IntegerField(default=0)

    class Meta:
        db_table = 'abonnements'
        ordering = ['-date_debut']

    def __str__(self):
        return f"{self.entreprise.nom} - {self.forfait.nom}"

    @property
    def jours_restants(self):
        if self.statut != 'ACTIF':
            return 0
        delta = self.date_fin - timezone.now()
        return max(0, delta.days)

    @property
    def heures_restantes(self):
        if self.statut != 'ACTIF':
            return 0
        delta = self.date_fin - timezone.now()
        return max(0, int(delta.total_seconds() / 3600))

    @property
    def pourcentage_restant(self):
        total = (self.date_fin - self.date_debut).days
        if total == 0: return 0
        return int((self.jours_restants / total) * 100)

    @property
    def est_expire(self):
        return self.date_fin < timezone.now()

    @property
    def pourcentage_ocr(self):
        if not self.forfait.max_factures_ocr_mois: return 0
        return int((self.factures_ocr_utilisees / self.forfait.max_factures_ocr_mois) * 100)

    def verifier_et_expirer(self):
        if self.est_expire and self.statut == 'ACTIF':
            self.statut = 'EXPIRE'
            self.save()
            return True
        return False


class Paiement(models.Model):
    """Historique des paiements"""
    METHODES = [
        ('MOBILE_MONEY', 'Mobile Money (Orange/MTN/Moov)'),
        ('CARTE', 'Carte bancaire'),
        ('VIREMENT', 'Virement bancaire'),
        ('ESPECES', 'Especes'),
        ('CHEQUE', 'Cheque'),
    ]
    STATUTS = [
        ('EN_ATTENTE', 'En attente'),
        ('VALIDE', 'Valide'),
        ('REFUSE', 'Refuse'),
        ('REMBOURSE', 'Rembourse'),
    ]

    reference = models.CharField(max_length=50, unique=True, blank=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='paiements')
    abonnement = models.ForeignKey(Abonnement, on_delete=models.SET_NULL, null=True, blank=True)
    forfait = models.ForeignKey(Forfait, on_delete=models.PROTECT)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    methode = models.CharField(max_length=20, choices=METHODES, default='MOBILE_MONEY')
    statut = models.CharField(max_length=20, choices=STATUTS, default='EN_ATTENTE')
    numero_transaction = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    paye_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    valide_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements_valides')
    created_at = models.DateTimeField(auto_now_add=True)
    valide_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'paiements'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.reference:
            year = timezone.now().year
            last = Paiement.objects.filter(reference__startswith=f'PAY-{year}').count() + 1
            self.reference = f'PAY-{year}-{last:05d}'
        super().save(*args, **kwargs)


def init_forfaits():
    """Initialise les 5 forfaits par defaut"""
    forfaits_data = [
        {
            'code': 'FREEMIUM', 'nom': 'Freemium (Essai 7 jours)', 'prix': 0, 'duree_jours': 7,
            'description': 'Essai gratuit pour decouvrir ComptaAuto',
            'max_factures_ocr_mois': 5, 'max_utilisateurs': 1, 'max_ecritures_mois': 20,
            'rapprochement_bancaire': False, 'reporting_avance': False,
            'couleur': '#6b8884', 'icone': 'bi-gift', 'ordre': 1,
        },
        {
            'code': 'STARTER', 'nom': 'Starter', 'prix': 25000, 'duree_jours': 30,
            'description': 'Pour les petites entreprises et auto-entrepreneurs',
            'max_factures_ocr_mois': 50, 'max_utilisateurs': 2, 'max_ecritures_mois': 200,
            'rapprochement_bancaire': True, 'reporting_avance': False,
            'couleur': '#14706b', 'icone': 'bi-rocket', 'ordre': 2,
        },
        {
            'code': 'PRO', 'nom': 'Pro', 'prix': 60000, 'duree_jours': 30,
            'description': 'Pour les PME en croissance',
            'max_factures_ocr_mois': 200, 'max_utilisateurs': 5, 'max_ecritures_mois': 1000,
            'rapprochement_bancaire': True, 'reporting_avance': True,
            'support_prioritaire': True,
            'couleur': '#1a8b85', 'icone': 'bi-stars', 'ordre': 3, 'populaire': True,
        },
        {
            'code': 'ENTERPRISE', 'nom': 'Enterprise', 'prix': 120000, 'duree_jours': 30,
            'description': 'Pour les grandes structures multi-sites',
            'max_factures_ocr_mois': 1000, 'max_utilisateurs': 20, 'max_ecritures_mois': 10000,
            'rapprochement_bancaire': True, 'reporting_avance': True,
            'support_prioritaire': True, 'export_illimite': True,
            'couleur': '#9b59b6', 'icone': 'bi-building', 'ordre': 4,
        },
        {
            'code': 'ANNUEL', 'nom': 'Annuel (12 mois)', 'prix': 300000, 'duree_jours': 365,
            'description': 'Pro pendant 12 mois - Economisez 50% !',
            'max_factures_ocr_mois': 200, 'max_utilisateurs': 5, 'max_ecritures_mois': 1000,
            'rapprochement_bancaire': True, 'reporting_avance': True,
            'support_prioritaire': True, 'export_illimite': True,
            'couleur': '#f4b860', 'icone': 'bi-trophy', 'ordre': 5,
        },
    ]

    for data in forfaits_data:
        Forfait.objects.update_or_create(code=data['code'], defaults=data)
'''

FILES["abonnements/views.py"] = '''from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import timedelta
from .models import Forfait, Abonnement, Paiement, init_forfaits
from accounts.models import Entreprise


@login_required
def tarifs(request):
    """Page publique des tarifs"""
    if not Forfait.objects.exists():
        init_forfaits()
    forfaits = Forfait.objects.filter(actif=True).order_by('ordre')

    abonnement_actuel = None
    if hasattr(request.user, 'entreprise'):
        abonnement_actuel = Abonnement.objects.filter(
            entreprise=request.user.entreprise, statut='ACTIF'
        ).first()

    return render(request, 'abonnements/tarifs.html', {
        'forfaits': forfaits,
        'abonnement_actuel': abonnement_actuel,
    })


@login_required
def mon_abonnement(request):
    """Page de gestion de l'abonnement de l'entreprise"""
    if not hasattr(request.user, 'entreprise'):
        return redirect('dashboard')

    entreprise = request.user.entreprise

    # Verifier expiration
    abo = Abonnement.objects.filter(entreprise=entreprise).order_by('-date_debut').first()
    if abo:
        abo.verifier_et_expirer()

    # Compter utilisation
    from ocr_app.models import FactureOCR
    from comptabilite.models import Ecriture
    debut_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0)

    nb_ocr_mois = FactureOCR.objects.filter(
        entreprise=entreprise, created_at__gte=debut_mois
    ).count()
    nb_ecr_mois = Ecriture.objects.filter(
        entreprise=entreprise, created_at__gte=debut_mois
    ).count()

    if abo:
        abo.factures_ocr_utilisees = nb_ocr_mois
        abo.ecritures_utilisees = nb_ecr_mois
        abo.save()

    historique = Abonnement.objects.filter(entreprise=entreprise).order_by('-date_debut')
    paiements = Paiement.objects.filter(entreprise=entreprise).order_by('-created_at')[:10]

    return render(request, 'abonnements/mon_abonnement.html', {
        'abonnement': abo,
        'historique': historique,
        'paiements': paiements,
        'nb_ocr_mois': nb_ocr_mois,
        'nb_ecr_mois': nb_ecr_mois,
    })


@login_required
def souscrire(request, forfait_code):
    """Souscrire a un forfait"""
    if not hasattr(request.user, 'entreprise'):
        return redirect('dashboard')

    forfait = get_object_or_404(Forfait, code=forfait_code, actif=True)

    if request.method == 'POST':
        # Creer le paiement (en attente de validation)
        paiement = Paiement.objects.create(
            entreprise=request.user.entreprise,
            forfait=forfait,
            montant=forfait.prix,
            methode=request.POST.get('methode', 'MOBILE_MONEY'),
            numero_transaction=request.POST.get('numero_transaction', ''),
            notes=request.POST.get('notes', ''),
            paye_par=request.user,
            statut='EN_ATTENTE',
        )

        # Si Freemium, validation automatique
        if forfait.code == 'FREEMIUM':
            paiement.statut = 'VALIDE'
            paiement.valide_at = timezone.now()
            paiement.save()
            creer_abonnement(paiement)
            messages.success(request, f"Votre essai Freemium de {forfait.duree_jours} jours est active !")
        else:
            # Notif admin pour validation
            from communication.models import Notification
            from accounts.models import User
            for admin in User.objects.filter(role='SUPER_ADMIN'):
                Notification.objects.create(
                    user=admin, type_notif='SYSTEME',
                    titre=f'Nouveau paiement a valider - {paiement.reference}',
                    message=f'{request.user.entreprise.nom} - {forfait.nom} - {forfait.prix} FCFA',
                    lien=f'/abonnements/admin/paiements/',
                )
            messages.success(request,
                f"Demande de souscription envoyee ! Reference : {paiement.reference}. "
                f"Votre abonnement sera active des validation du paiement.")

        return redirect('mon_abonnement')

    return render(request, 'abonnements/souscrire.html', {'forfait': forfait})


def creer_abonnement(paiement):
    """Cree un nouvel abonnement apres paiement valide"""
    # Si abonnement actif existe, le marquer expire
    Abonnement.objects.filter(
        entreprise=paiement.entreprise, statut='ACTIF'
    ).update(statut='EXPIRE')

    abo = Abonnement.objects.create(
        entreprise=paiement.entreprise,
        forfait=paiement.forfait,
        date_fin=timezone.now() + timedelta(days=paiement.forfait.duree_jours),
        statut='ACTIF',
    )
    paiement.abonnement = abo
    paiement.save()

    # Mettre a jour formule entreprise
    if paiement.forfait.code == 'STARTER':
        paiement.entreprise.formule = 'STARTER'
    elif paiement.forfait.code in ['PRO', 'ANNUEL']:
        paiement.entreprise.formule = 'BUSINESS'
    elif paiement.forfait.code == 'ENTERPRISE':
        paiement.entreprise.formule = 'ENTERPRISE'
    paiement.entreprise.save()

    # Notif entreprise
    from communication.models import Notification
    Notification.objects.create(
        user=paiement.entreprise.responsable, type_notif='SYSTEME',
        titre=f'Abonnement {paiement.forfait.nom} active !',
        message=f'Votre abonnement est actif jusqu\\'au {abo.date_fin.strftime("%d/%m/%Y")}',
        lien='/abonnements/mon-abonnement/',
    )

    return abo


# ============ ADMIN ============

@login_required
def admin_paiements(request):
    """Page admin de gestion des paiements"""
    if not request.user.is_super_admin:
        return redirect('dashboard')

    paiements = Paiement.objects.all().select_related('entreprise', 'forfait')

    # Stats
    total_revenu = sum(float(p.montant) for p in paiements.filter(statut='VALIDE'))
    nb_en_attente = paiements.filter(statut='EN_ATTENTE').count()
    nb_valides = paiements.filter(statut='VALIDE').count()

    return render(request, 'abonnements/admin_paiements.html', {
        'paiements': paiements,
        'total_revenu': total_revenu,
        'nb_en_attente': nb_en_attente,
        'nb_valides': nb_valides,
    })


@login_required
def valider_paiement(request, pk):
    """Admin : valider un paiement"""
    if not request.user.is_super_admin:
        return JsonResponse({'error': 'Non autorise'}, status=403)

    paiement = get_object_or_404(Paiement, pk=pk)
    if paiement.statut != 'EN_ATTENTE':
        return JsonResponse({'error': 'Paiement deja traite'}, status=400)

    paiement.statut = 'VALIDE'
    paiement.valide_par = request.user
    paiement.valide_at = timezone.now()
    paiement.save()

    # Creer abonnement
    creer_abonnement(paiement)

    return JsonResponse({'status': 'ok'})


@login_required
def refuser_paiement(request, pk):
    """Admin : refuser un paiement"""
    if not request.user.is_super_admin:
        return JsonResponse({'error': 'Non autorise'}, status=403)

    paiement = get_object_or_404(Paiement, pk=pk)
    paiement.statut = 'REFUSE'
    paiement.valide_par = request.user
    paiement.notes += f"\\nRefuse par {request.user.get_full_name()} le {timezone.now()}"
    paiement.save()

    # Notif entreprise
    from communication.models import Notification
    Notification.objects.create(
        user=paiement.entreprise.responsable, type_notif='SYSTEME',
        titre=f'Paiement refuse - {paiement.reference}',
        message=f'Votre paiement de {paiement.montant} FCFA a ete refuse. Contactez le support.',
        lien='/communication/messagerie/',
    )
    return JsonResponse({'status': 'ok'})


@login_required
def admin_abonnements(request):
    """Vue d'ensemble des abonnements"""
    if not request.user.is_super_admin:
        return redirect('dashboard')

    abonnements = Abonnement.objects.all().select_related('entreprise', 'forfait')

    # Verifier expirations
    for abo in abonnements:
        abo.verifier_et_expirer()

    # Stats par forfait
    from django.db.models import Count, Sum
    stats_forfaits = Forfait.objects.annotate(
        nb_abonnes=Count('abonnement', filter=models.Q(abonnement__statut='ACTIF'))
    )

    return render(request, 'abonnements/admin_abonnements.html', {
        'abonnements': abonnements,
        'stats_forfaits': stats_forfaits,
    })


def telecharger_facture(request, pk):
    """Telecharger facture PDF d'un paiement"""
    paiement = get_object_or_404(Paiement, pk=pk)

    # Verifier acces
    if not request.user.is_super_admin:
        if not hasattr(request.user, 'entreprise') or paiement.entreprise != request.user.entreprise:
            return redirect('dashboard')

    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from io import BytesIO

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("<b>FACTURE</b>", styles['Title']))
    elements.append(Paragraph(f"<b>ComptaAuto SaaS</b>", styles['Heading2']))
    elements.append(Paragraph(f"Reference : {paiement.reference}", styles['Normal']))
    elements.append(Paragraph(f"Date : {paiement.created_at.strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"<b>Facture a :</b>", styles['Heading3']))
    elements.append(Paragraph(f"{paiement.entreprise.nom}", styles['Normal']))
    elements.append(Paragraph(f"{paiement.entreprise.email_contact}", styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [
        ['Designation', 'Montant'],
        [f'Abonnement {paiement.forfait.nom}', f'{paiement.montant:,.0f} FCFA'],
        [f'Duree : {paiement.forfait.duree_jours} jours', ''],
        ['', ''],
        ['TOTAL', f'{paiement.montant:,.0f} FCFA'],
    ]
    t = Table(data, colWidths=[350, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#14706b')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f4b860')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 30))

    elements.append(Paragraph(f"<b>Statut :</b> {paiement.get_statut_display()}", styles['Normal']))
    elements.append(Paragraph(f"<b>Methode :</b> {paiement.get_methode_display()}", styles['Normal']))
    if paiement.numero_transaction:
        elements.append(Paragraph(f"<b>Transaction :</b> {paiement.numero_transaction}", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="facture_{paiement.reference}.pdf"'
    return response
'''

# Note : on doit corriger l'import models dans views.py
FILES["abonnements/views.py"] = FILES["abonnements/views.py"].replace(
    "filter=models.Q",
    "filter=__import__('django').db.models.Q"
)

FILES["abonnements/urls.py"] = '''from django.urls import path
from . import views

urlpatterns = [
    path('tarifs/', views.tarifs, name='tarifs'),
    path('mon-abonnement/', views.mon_abonnement, name='mon_abonnement'),
    path('souscrire/<str:forfait_code>/', views.souscrire, name='souscrire'),
    path('facture/<int:pk>/pdf/', views.telecharger_facture, name='telecharger_facture'),

    # Admin
    path('admin/paiements/', views.admin_paiements, name='admin_paiements'),
    path('admin/paiements/<int:pk>/valider/', views.valider_paiement, name='valider_paiement'),
    path('admin/paiements/<int:pk>/refuser/', views.refuser_paiement, name='refuser_paiement'),
    path('admin/abonnements/', views.admin_abonnements, name='admin_abonnements'),
]
'''

FILES["abonnements/admin.py"] = '''from django.contrib import admin
from .models import Forfait, Abonnement, Paiement

@admin.register(Forfait)
class ForfaitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'prix', 'duree_jours', 'actif', 'populaire')
    list_filter = ('actif', 'populaire')

@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):
    list_display = ('entreprise', 'forfait', 'date_debut', 'date_fin', 'statut')
    list_filter = ('statut', 'forfait')

@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('reference', 'entreprise', 'forfait', 'montant', 'methode', 'statut', 'created_at')
    list_filter = ('statut', 'methode', 'forfait')
'''

# ============================================
# MIDDLEWARE : verification abonnement
# ============================================
FILES["abonnements/middleware.py"] = '''from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse


class AbonnementMiddleware:
    """Verifie que l'entreprise a un abonnement actif"""

    EXEMPT_URLS = [
        '/login/', '/logout/', '/register/', '/demo/',
        '/abonnements/', '/communication/', '/notifications/',
        '/django-admin/', '/static/', '/media/',
        '/admin-panel/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Super admin pas de restriction
        if request.user.is_super_admin:
            return self.get_response(request)

        # Verifier exempt URLs
        path = request.path
        for url in self.EXEMPT_URLS:
            if path.startswith(url):
                return self.get_response(request)

        # Verifier abonnement
        if hasattr(request.user, 'entreprise'):
            from .models import Abonnement
            abo = Abonnement.objects.filter(
                entreprise=request.user.entreprise, statut='ACTIF'
            ).order_by('-date_debut').first()

            if not abo:
                messages.warning(request, "Vous n'avez pas d'abonnement actif. Choisissez un forfait pour continuer.")
                return redirect('tarifs')

            if abo.verifier_et_expirer():
                messages.error(request, f"Votre abonnement {abo.forfait.nom} a expire. Renouvelez pour continuer.")
                return redirect('tarifs')

        return self.get_response(request)


def context_abonnement(request):
    """Context processor pour acceder a l'abonnement partout"""
    if not request.user.is_authenticated:
        return {}
    if request.user.is_super_admin:
        return {'is_super_admin': True}
    if hasattr(request.user, 'entreprise'):
        from .models import Abonnement
        abo = Abonnement.objects.filter(
            entreprise=request.user.entreprise, statut='ACTIF'
        ).order_by('-date_debut').first()
        return {'abonnement_actif': abo}
    return {}
'''

# ============================================
# UPDATE REGISTER pour creer freemium auto
# ============================================
FILES["accounts/views.py"] = '''from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
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
        entreprise = Entreprise.objects.create(
            nom=request.POST.get('nom_entreprise'), secteur=request.POST.get('secteur'),
            email_contact=user.email, responsable=user)

        # Creer abonnement Freemium automatique de 7 jours
        try:
            from abonnements.models import Forfait, Abonnement, Paiement, init_forfaits
            if not Forfait.objects.exists():
                init_forfaits()
            freemium = Forfait.objects.get(code='FREEMIUM')
            paiement = Paiement.objects.create(
                entreprise=entreprise, forfait=freemium,
                montant=0, methode='ESPECES',
                statut='VALIDE', paye_par=user,
                valide_at=timezone.now(),
                notes='Activation automatique Freemium a l\\'inscription',
            )
            abo = Abonnement.objects.create(
                entreprise=entreprise, forfait=freemium,
                date_fin=timezone.now() + timedelta(days=7),
                statut='ACTIF',
            )
            paiement.abonnement = abo
            paiement.save()
            messages.success(request,
                "Compte cree ! Vous beneficiez de 7 jours d'essai gratuit. Connectez-vous.")
        except Exception as e:
            print(f"Erreur init freemium: {e}")
            messages.success(request, "Compte cree ! Connectez-vous.")

        return redirect('login')
    return render(request, 'accounts/register.html')


def logout_view(request):
    auth_logout(request)
    return redirect('login')


def load_demo(request):
    from django.utils import timezone
    from datetime import timedelta
    if not User.objects.filter(email='admin@comptaauto.ci').exists():
        User.objects.create_user(email='admin@comptaauto.ci', username='admin', password='Admin2026!',
            first_name='KONE', last_name="N'GAZANA MOHAMED", role=User.Role.SUPER_ADMIN, is_staff=True, is_superuser=True)
    if not User.objects.filter(email='jeancome@jkof.ci').exists():
        u = User.objects.create_user(email='jeancome@jkof.ci', username='jeancome', password='Demo2026!',
            first_name='MR JEAN', last_name='COME', role=User.Role.ENTREPRISE)
        entreprise = Entreprise.objects.create(nom='JKOF CONSULTING', secteur='BTP',
            email_contact='zanamohamedkone@gmail.com', responsable=u)

        # Donner un Pro de demo
        try:
            from abonnements.models import Forfait, Abonnement, init_forfaits
            if not Forfait.objects.exists():
                init_forfaits()
            pro = Forfait.objects.get(code='PRO')
            Abonnement.objects.create(
                entreprise=entreprise, forfait=pro,
                date_fin=timezone.now() + timedelta(days=30),
                statut='ACTIF',
            )
        except Exception as e:
            print(f"Erreur: {e}")

    messages.success(request, "Demo OK ! Admin: admin@comptaauto.ci/Admin2026! | Entreprise: jeancome@jkof.ci/Demo2026!")
    return redirect('login')
'''

# ============================================
# TEMPLATES
# ============================================

FILES["templates/abonnements/tarifs.html"] = '''{% extends 'base.html' %}{% block title %}Tarifs ComptaAuto{% endblock %}{% block content %}
{% if user.is_authenticated %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">
{% endif %}

<div class="container py-5">
<div class="text-center mb-5">
<h1 style="font-family:'Playfair Display',serif;">Nos forfaits</h1>
<p class="text-muted">Choisissez la formule adaptee a votre entreprise</p>
</div>

{% if abonnement_actuel %}
<div class="alert alert-info text-center mb-4">
<i class="bi bi-info-circle"></i> Vous etes actuellement sur le forfait <strong>{{ abonnement_actuel.forfait.nom }}</strong> ({{ abonnement_actuel.jours_restants }} jours restants)
</div>
{% endif %}

<div class="row g-4 justify-content-center">
{% for f in forfaits %}
<div class="col-md-4 col-lg-3">
<div class="card h-100 {% if f.populaire %}border-primary shadow-lg{% endif %}" style="border-top: 5px solid {{ f.couleur }};">
{% if f.populaire %}<div class="position-absolute top-0 start-50 translate-middle"><span class="badge bg-primary">POPULAIRE</span></div>{% endif %}
<div class="card-body text-center">
<i class="bi {{ f.icone }}" style="font-size:3rem;color:{{ f.couleur }};"></i>
<h3 class="mt-3" style="color:{{ f.couleur }};">{{ f.nom }}</h3>
<div class="my-4">
{% if f.prix == 0 %}
<h2 class="text-success">GRATUIT</h2>
<small class="text-muted">{{ f.duree_jours }} jours d'essai</small>
{% else %}
<h2>{{ f.prix|floatformat:0 }} <small>FCFA</small></h2>
<small class="text-muted">{% if f.duree_jours >= 365 %}/ {{ f.duree_jours }} jours ({% widthratio f.duree_jours 30 1 %} mois){% else %}/ {{ f.duree_jours }} jours{% endif %}</small>
{% endif %}
</div>
<p class="text-muted small">{{ f.description }}</p>
<hr>
<ul class="list-unstyled text-start small">
<li><i class="bi bi-check-circle text-success"></i> {{ f.max_factures_ocr_mois }} factures OCR/mois</li>
<li><i class="bi bi-check-circle text-success"></i> {{ f.max_utilisateurs }} utilisateur(s)</li>
<li><i class="bi bi-check-circle text-success"></i> {{ f.max_ecritures_mois }} ecritures/mois</li>
<li><i class="bi bi-{% if f.rapprochement_bancaire %}check-circle text-success{% else %}x-circle text-muted{% endif %}"></i> Rapprochement bancaire</li>
<li><i class="bi bi-{% if f.reporting_avance %}check-circle text-success{% else %}x-circle text-muted{% endif %}"></i> Reporting avance</li>
<li><i class="bi bi-{% if f.support_prioritaire %}check-circle text-success{% else %}x-circle text-muted{% endif %}"></i> Support prioritaire</li>
<li><i class="bi bi-{% if f.export_illimite %}check-circle text-success{% else %}x-circle text-muted{% endif %}"></i> Export illimite</li>
</ul>
{% if user.is_authenticated and not user.is_super_admin %}
{% if abonnement_actuel.forfait.code == f.code %}
<button class="btn btn-secondary w-100 mt-3" disabled>Forfait actuel</button>
{% else %}
<a href="{% url 'souscrire' f.code %}" class="btn w-100 mt-3" style="background:{{ f.couleur }};color:white;">
{% if f.prix == 0 %}Essayer gratuit{% else %}Souscrire{% endif %}
</a>
{% endif %}
{% else %}
<a href="{% url 'login' %}" class="btn btn-outline-primary w-100 mt-3">Se connecter</a>
{% endif %}
</div>
</div>
</div>
{% endfor %}
</div>

<div class="text-center mt-5">
<p class="text-muted">Besoin d'un forfait personnalise ? <a href="{% url 'nouvelle_conversation' %}">Contactez-nous</a></p>
</div>
</div>

{% if user.is_authenticated %}
</div></main></div>
{% endif %}
{% endblock %}
'''

FILES["templates/abonnements/mon_abonnement.html"] = '''{% extends 'base.html' %}{% block page_title %}Mon abonnement{% endblock %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">

{% if abonnement %}
<div class="card mb-4" style="border-top: 5px solid {{ abonnement.forfait.couleur }};">
<div class="card-body">
<div class="row align-items-center">
<div class="col-md-3 text-center">
<i class="bi {{ abonnement.forfait.icone }}" style="font-size:4rem;color:{{ abonnement.forfait.couleur }};"></i>
<h4 class="mt-2">{{ abonnement.forfait.nom }}</h4>
<span class="badge bg-{% if abonnement.statut == 'ACTIF' %}success{% else %}danger{% endif %}">{{ abonnement.get_statut_display }}</span>
</div>
<div class="col-md-5">
<h5>Periode</h5>
<p>Du <strong>{{ abonnement.date_debut|date:"d/m/Y" }}</strong> au <strong>{{ abonnement.date_fin|date:"d/m/Y" }}</strong></p>
<div class="progress mb-2" style="height:25px;">
<div class="progress-bar bg-success" style="width:{{ abonnement.pourcentage_restant }}%">
{{ abonnement.jours_restants }} jours restants
</div>
</div>
{% if abonnement.jours_restants <= 7 %}
<div class="alert alert-warning mt-2"><i class="bi bi-exclamation-triangle"></i> Votre abonnement expire bientot !</div>
{% endif %}
</div>
<div class="col-md-4 text-end">
<a href="{% url 'tarifs' %}" class="btn btn-connect"><i class="bi bi-arrow-up-circle"></i> Changer / Renouveler</a>
</div>
</div>
</div>
</div>

<div class="row g-4 mb-4">
<div class="col-md-6">
<div class="card"><div class="card-body">
<h5><i class="bi bi-file-earmark-text"></i> Factures OCR utilisees ce mois</h5>
<div class="progress mb-2" style="height:30px;">
<div class="progress-bar {% if abonnement.pourcentage_ocr > 80 %}bg-danger{% elif abonnement.pourcentage_ocr > 50 %}bg-warning{% else %}bg-success{% endif %}" style="width:{{ abonnement.pourcentage_ocr }}%">
{{ nb_ocr_mois }} / {{ abonnement.forfait.max_factures_ocr_mois }}
</div>
</div>
<small class="text-muted">{{ abonnement.forfait.max_factures_ocr_mois|add:nb_ocr_mois|add:'-'|add:nb_ocr_mois }} restantes ce mois</small>
</div></div>
</div>
<div class="col-md-6">
<div class="card"><div class="card-body">
<h5><i class="bi bi-journal-text"></i> Ecritures ce mois</h5>
<div class="progress mb-2" style="height:30px;">
<div class="progress-bar bg-info" style="width:{% widthratio nb_ecr_mois abonnement.forfait.max_ecritures_mois 100 %}%">
{{ nb_ecr_mois }} / {{ abonnement.forfait.max_ecritures_mois }}
</div>
</div>
</div></div>
</div>
</div>

{% else %}
<div class="alert alert-warning text-center">
<h4><i class="bi bi-exclamation-circle"></i> Aucun abonnement actif</h4>
<p>Vous devez choisir un forfait pour utiliser ComptaAuto.</p>
<a href="{% url 'tarifs' %}" class="btn btn-connect btn-lg">Voir les forfaits</a>
</div>
{% endif %}

<div class="card mb-4"><div class="card-body">
<h4>Historique des paiements</h4>
<table class="table">
<thead><tr><th>Reference</th><th>Date</th><th>Forfait</th><th>Montant</th><th>Methode</th><th>Statut</th><th></th></tr></thead>
<tbody>
{% for p in paiements %}
<tr>
<td><strong>{{ p.reference }}</strong></td>
<td>{{ p.created_at|date:"d/m/Y H:i" }}</td>
<td>{{ p.forfait.nom }}</td>
<td>{{ p.montant|floatformat:0 }} FCFA</td>
<td>{{ p.get_methode_display }}</td>
<td><span class="badge bg-{% if p.statut == 'VALIDE' %}success{% elif p.statut == 'EN_ATTENTE' %}warning{% elif p.statut == 'REFUSE' %}danger{% else %}secondary{% endif %}">{{ p.get_statut_display }}</span></td>
<td><a href="{% url 'telecharger_facture' p.pk %}" class="btn btn-sm btn-outline-primary"><i class="bi bi-file-pdf"></i></a></td>
</tr>
{% empty %}<tr><td colspan="7" class="text-center text-muted">Aucun paiement</td></tr>{% endfor %}
</tbody></table>
</div></div>

<div class="card"><div class="card-body">
<h4>Historique des abonnements</h4>
<table class="table">
<thead><tr><th>Forfait</th><th>Debut</th><th>Fin</th><th>Statut</th></tr></thead>
<tbody>
{% for h in historique %}
<tr>
<td><strong>{{ h.forfait.nom }}</strong></td>
<td>{{ h.date_debut|date:"d/m/Y" }}</td>
<td>{{ h.date_fin|date:"d/m/Y" }}</td>
<td><span class="badge bg-{% if h.statut == 'ACTIF' %}success{% else %}secondary{% endif %}">{{ h.get_statut_display }}</span></td>
</tr>
{% endfor %}
</tbody></table>
</div></div>

</div></main></div>
{% endblock %}
'''

FILES["templates/abonnements/souscrire.html"] = '''{% extends 'base.html' %}{% block page_title %}Souscrire - {{ forfait.nom }}{% endblock %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">

<a href="{% url 'tarifs' %}" class="btn btn-link"><i class="bi bi-arrow-left"></i> Retour aux tarifs</a>

<div class="row g-4 mt-3">
<div class="col-md-5">
<div class="card" style="border-top: 5px solid {{ forfait.couleur }};">
<div class="card-body text-center">
<i class="bi {{ forfait.icone }}" style="font-size:4rem;color:{{ forfait.couleur }};"></i>
<h3 class="mt-2" style="color:{{ forfait.couleur }};">{{ forfait.nom }}</h3>
<h1 class="my-3">{% if forfait.prix == 0 %}<span class="text-success">GRATUIT</span>{% else %}{{ forfait.prix|floatformat:0 }} FCFA{% endif %}</h1>
<p class="text-muted">{{ forfait.duree_jours }} jours d'acces</p>
<hr>
<ul class="list-unstyled text-start small">
<li>✅ {{ forfait.max_factures_ocr_mois }} factures OCR/mois</li>
<li>✅ {{ forfait.max_utilisateurs }} utilisateur(s)</li>
<li>✅ {{ forfait.max_ecritures_mois }} ecritures/mois</li>
{% if forfait.rapprochement_bancaire %}<li>✅ Rapprochement bancaire</li>{% endif %}
{% if forfait.reporting_avance %}<li>✅ Reporting avance</li>{% endif %}
{% if forfait.support_prioritaire %}<li>✅ Support prioritaire</li>{% endif %}
{% if forfait.export_illimite %}<li>✅ Export illimite</li>{% endif %}
</ul>
</div>
</div>
</div>

<div class="col-md-7">
<div class="card"><div class="card-body">
{% if forfait.code == 'FREEMIUM' %}
<h4><i class="bi bi-gift"></i> Activation Freemium</h4>
<p>Cliquez sur le bouton ci-dessous pour activer immediatement votre essai gratuit de 7 jours.</p>
<form method="POST">{% csrf_token %}
<input type="hidden" name="methode" value="ESPECES">
<button type="submit" class="btn btn-success btn-lg w-100"><i class="bi bi-check-circle"></i> Activer l'essai gratuit</button>
</form>
{% else %}
<h4><i class="bi bi-credit-card"></i> Modalites de paiement</h4>
<p class="text-muted">Choisissez votre methode de paiement</p>

<div class="alert alert-info">
<strong>Comment payer ?</strong><br>
<strong>Mobile Money :</strong> Orange Money : +225 0707 12 34 56 - MTN MoMo : +225 0506 78 90 12<br>
<strong>Virement bancaire :</strong> IBAN CI93 CI00 1234 5678 9012 3456 78<br>
Une fois le paiement effectue, remplissez ce formulaire et notre equipe validera dans les 24h.
</div>

<form method="POST">{% csrf_token %}
<div class="mb-3"><label>Methode de paiement</label>
<select name="methode" class="form-select" required>
<option value="MOBILE_MONEY">Mobile Money (Orange/MTN/Moov)</option>
<option value="CARTE">Carte bancaire</option>
<option value="VIREMENT">Virement bancaire</option>
<option value="ESPECES">Especes</option>
<option value="CHEQUE">Cheque</option>
</select>
</div>
<div class="mb-3"><label>Numero de transaction (optionnel)</label>
<input type="text" name="numero_transaction" class="form-control" placeholder="Ex: MP240615.1234.A56789">
<small class="text-muted">Reference du paiement Mobile Money ou autre</small>
</div>
<div class="mb-3"><label>Notes (optionnel)</label>
<textarea name="notes" class="form-control" rows="3" placeholder="Informations complementaires..."></textarea>
</div>

<div class="alert alert-warning">
<strong>Montant a payer : {{ forfait.prix|floatformat:0 }} FCFA</strong>
</div>

<button type="submit" class="btn btn-connect btn-lg w-100"><i class="bi bi-check-circle"></i> Confirmer la souscription</button>
</form>
{% endif %}
</div></div>
</div>
</div>

</div></main></div>
{% endblock %}
'''

FILES["templates/abonnements/admin_paiements.html"] = '''{% extends 'base.html' %}{% block content %}
<div class="admin-layout">
<header class="admin-header">
<div class="logo-wrapper"><div class="logo-icon">C</div><div><h1 class="brand-title" style="color:#1a3e3a;">ComptaAuto</h1><p class="brand-subtitle text-muted">CONSOLE ADMIN</p></div></div>
<div><a href="{% url 'admin_dashboard' %}" class="btn btn-outline-primary btn-sm me-2"><i class="bi bi-arrow-left"></i> Dashboard</a><a href="{% url 'logout' %}" class="btn btn-outline-danger btn-sm">Deconnexion</a></div>
</header>
<main class="container-fluid py-4">

<h2 style="font-family:'Playfair Display',serif;">Gestion des paiements</h2>

<div class="row g-4 my-3">
<div class="col-md-4"><div class="stat-card"><div class="stat-icon bg-orange-light"><i class="bi bi-hourglass-split"></i></div><div class="stat-value">{{ nb_en_attente }}</div><div class="stat-label">En attente</div></div></div>
<div class="col-md-4"><div class="stat-card"><div class="stat-icon bg-teal-light"><i class="bi bi-check-circle"></i></div><div class="stat-value">{{ nb_valides }}</div><div class="stat-label">Valides</div></div></div>
<div class="col-md-4"><div class="stat-card"><div class="stat-icon bg-teal-light"><i class="bi bi-currency-exchange"></i></div><div class="stat-value">{{ total_revenu|floatformat:0 }}</div><div class="stat-label">Revenus totaux (FCFA)</div></div></div>
</div>

<div class="card mt-4"><div class="card-body">
<h4>Tous les paiements</h4>
<table class="table align-middle">
<thead><tr><th>Reference</th><th>Entreprise</th><th>Forfait</th><th>Montant</th><th>Methode</th><th>Transaction</th><th>Date</th><th>Statut</th><th>Actions</th></tr></thead>
<tbody>
{% for p in paiements %}
<tr>
<td><strong>{{ p.reference }}</strong></td>
<td>{{ p.entreprise.nom }}<br><small class="text-muted">{{ p.entreprise.email_contact }}</small></td>
<td><span class="badge bg-light text-dark">{{ p.forfait.nom }}</span></td>
<td><strong>{{ p.montant|floatformat:0 }} F</strong></td>
<td>{{ p.get_methode_display }}</td>
<td><small>{{ p.numero_transaction|default:"-" }}</small></td>
<td>{{ p.created_at|date:"d/m/Y H:i" }}</td>
<td><span class="badge bg-{% if p.statut == 'VALIDE' %}success{% elif p.statut == 'EN_ATTENTE' %}warning{% elif p.statut == 'REFUSE' %}danger{% else %}secondary{% endif %}">{{ p.get_statut_display }}</span></td>
<td>
{% if p.statut == 'EN_ATTENTE' %}
<button class="btn btn-sm btn-success" onclick="valider({{ p.pk }})"><i class="bi bi-check"></i></button>
<button class="btn btn-sm btn-danger" onclick="refuser({{ p.pk }})"><i class="bi bi-x"></i></button>
{% endif %}
<a href="{% url 'telecharger_facture' p.pk %}" class="btn btn-sm btn-outline-primary"><i class="bi bi-file-pdf"></i></a>
</td>
</tr>
{% empty %}<tr><td colspan="9" class="text-center text-muted">Aucun paiement</td></tr>{% endfor %}
</tbody></table>
</div></div>

</main></div>
<script>
function getCookie(n){const v=`; ${document.cookie}`.split(`; ${n}=`);if(v.length===2)return v.pop().split(';').shift();}
async function valider(id){if(!confirm('Valider ce paiement ?'))return;const r=await fetch('/abonnements/admin/paiements/'+id+'/valider/',{method:'POST',headers:{'X-CSRFToken':getCookie('csrftoken')}});if(r.ok)location.reload();}
async function refuser(id){if(!confirm('REFUSER ce paiement ?'))return;const r=await fetch('/abonnements/admin/paiements/'+id+'/refuser/',{method:'POST',headers:{'X-CSRFToken':getCookie('csrftoken')}});if(r.ok)location.reload();}
</script>
{% endblock %}
'''

FILES["templates/abonnements/admin_abonnements.html"] = '''{% extends 'base.html' %}{% block content %}
<div class="admin-layout">
<header class="admin-header">
<div class="logo-wrapper"><div class="logo-icon">C</div><div><h1 class="brand-title" style="color:#1a3e3a;">ComptaAuto</h1><p class="brand-subtitle text-muted">CONSOLE ADMIN</p></div></div>
<div><a href="{% url 'admin_dashboard' %}" class="btn btn-outline-primary btn-sm me-2"><i class="bi bi-arrow-left"></i> Dashboard</a><a href="{% url 'logout' %}" class="btn btn-outline-danger btn-sm">Deconnexion</a></div>
</header>
<main class="container-fluid py-4">

<h2 style="font-family:'Playfair Display',serif;">Tous les abonnements</h2>

<div class="row g-4 my-3">
{% for f in stats_forfaits %}
<div class="col-md-2"><div class="card text-center" style="border-top: 4px solid {{ f.couleur }};">
<div class="card-body">
<i class="bi {{ f.icone }}" style="font-size:2rem;color:{{ f.couleur }};"></i>
<h3>{{ f.nb_abonnes }}</h3>
<small class="text-muted">{{ f.nom }}</small>
</div></div></div>
{% endfor %}
</div>

<div class="card mt-4"><div class="card-body">
<table class="table align-middle">
<thead><tr><th>Entreprise</th><th>Forfait</th><th>Debut</th><th>Fin</th><th>Jours restants</th><th>OCR utilises</th><th>Statut</th></tr></thead>
<tbody>
{% for a in abonnements %}
<tr>
<td><strong>{{ a.entreprise.nom }}</strong></td>
<td><span class="badge" style="background:{{ a.forfait.couleur }};">{{ a.forfait.nom }}</span></td>
<td>{{ a.date_debut|date:"d/m/Y" }}</td>
<td>{{ a.date_fin|date:"d/m/Y" }}</td>
<td>{% if a.statut == 'ACTIF' %}<span class="badge bg-{% if a.jours_restants <= 3 %}danger{% elif a.jours_restants <= 7 %}warning{% else %}success{% endif %}">{{ a.jours_restants }} j</span>{% else %}-{% endif %}</td>
<td>{{ a.factures_ocr_utilisees }}/{{ a.forfait.max_factures_ocr_mois }}</td>
<td><span class="badge bg-{% if a.statut == 'ACTIF' %}success{% else %}secondary{% endif %}">{{ a.get_statut_display }}</span></td>
</tr>
{% empty %}<tr><td colspan="7" class="text-center text-muted">Aucun abonnement</td></tr>{% endfor %}
</tbody></table>
</div></div>

</main></div>
{% endblock %}
'''

# ============================================
# UPDATE SIDEBAR pour ajouter abonnement
# ============================================
FILES["templates/partials/sidebar.html"] = '''<aside class="sidebar">
<div class="sidebar-brand"><div class="logo-icon">C</div><div><h1 class="brand-title">ComptaAuto</h1><p class="brand-subtitle">COMPTABILITE</p></div></div>

{% if abonnement_actif %}
<div class="alert alert-{% if abonnement_actif.jours_restants <= 3 %}danger{% elif abonnement_actif.jours_restants <= 7 %}warning{% else %}info{% endif %} py-2 px-3 mb-3" style="font-size:0.85rem;">
<strong>{{ abonnement_actif.forfait.nom }}</strong><br>
<small>{{ abonnement_actif.jours_restants }} jours restants</small>
{% if abonnement_actif.jours_restants <= 7 %}<br><a href="{% url 'tarifs' %}" class="btn btn-sm btn-warning mt-2">Renouveler</a>{% endif %}
</div>
{% endif %}

<div class="sidebar-section">PILOTAGE</div>
<nav class="sidebar-nav"><a href="{% url 'dashboard' %}" class="nav-item {% if request.resolver_match.url_name == 'dashboard' %}active{% endif %}"><i class="bi bi-grid-1x2"></i> Tableau de bord</a></nav>

<div class="sidebar-section">OPERATIONS</div>
<nav class="sidebar-nav">
<a href="{% url 'ocr_page' %}" class="nav-item {% if 'ocr' in request.path %}active{% endif %}"><i class="bi bi-text-paragraph"></i> Saisie OCR</a>
<a href="{% url 'rapprochement_page' %}" class="nav-item {% if 'rapprochement' in request.path %}active{% endif %}"><i class="bi bi-arrow-left-right"></i> Rapprochement</a>
<a href="{% url 'ecritures' %}" class="nav-item {% if 'ecriture' in request.path %}active{% endif %}"><i class="bi bi-journal-text"></i> Ecritures</a>
<a href="{% url 'nouvelle_ecriture' %}" class="nav-item"><i class="bi bi-plus-circle"></i> Nouvelle ecriture</a>
</nav>

<div class="sidebar-section">REPORTING & ALERTES</div>
<nav class="sidebar-nav">
<a href="{% url 'reporting_index' %}" class="nav-item {% if 'reporting' in request.path %}active{% endif %}"><i class="bi bi-bar-chart-line"></i> Reporting financier</a>
<a href="{% url 'alertes_page' %}" class="nav-item {% if 'alerte' in request.path %}active{% endif %}"><i class="bi bi-bell"></i> Alertes</a>
</nav>

<div class="sidebar-section">SUPPORT</div>
<nav class="sidebar-nav">
<a href="{% url 'messagerie' %}" class="nav-item {% if 'conversation' in request.path or 'messagerie' in request.path %}active{% endif %}"><i class="bi bi-chat-dots"></i> Messagerie</a>
<a href="{% url 'tickets_list' %}" class="nav-item {% if 'ticket' in request.path %}active{% endif %}"><i class="bi bi-ticket-perforated"></i> Tickets support</a>
<a href="{% url 'annonces_list' %}" class="nav-item {% if 'annonce' in request.path %}active{% endif %}"><i class="bi bi-megaphone"></i> Annonces</a>
<a href="{% url 'rappels_list' %}" class="nav-item {% if 'rappel' in request.path %}active{% endif %}"><i class="bi bi-telephone"></i> Demandes rappel</a>
</nav>

<div class="sidebar-section">ABONNEMENT</div>
<nav class="sidebar-nav">
<a href="{% url 'mon_abonnement' %}" class="nav-item {% if 'mon-abonnement' in request.path %}active{% endif %}"><i class="bi bi-credit-card"></i> Mon abonnement</a>
<a href="{% url 'tarifs' %}" class="nav-item {% if 'tarifs' in request.path %}active{% endif %}"><i class="bi bi-tags"></i> Tarifs</a>
</nav>

<div class="sidebar-section">CONFIGURATION</div>
<nav class="sidebar-nav">
<a href="{% url 'init_plan' %}" class="nav-item"><i class="bi bi-list-ol"></i> Initialiser plan</a>
</nav>

<div class="sidebar-footer"><strong>{{ user.entreprise.nom|default:user.get_full_name }}</strong><small>SYSCOHADA - Exercice {{ user.entreprise.exercice_courant|default:'2026' }}</small></div>
</aside>
'''

# ============================================
# UPDATE SETTINGS + URLS
# ============================================
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
    'rapprochement','reporting','alertes','communication','abonnements',
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
    path('rapprochement/', include('rapprochement.urls')),
    path('reporting/', include('reporting.urls')),
    path('alertes/', include('alertes.urls')),
    path('communication/', include('communication.urls')),
    path('abonnements/', include('abonnements.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
'''

# Ecriture
for fp, content in FILES.items():
    p = BASE / fp
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"      [OK] {fp}")

print(f"\n      {len(FILES)} fichiers crees/mis a jour\n")

# Migrations
print("[3/3] Migrations base de donnees...")
subprocess.run([PY, "manage.py", "makemigrations", "abonnements"], check=True)
subprocess.run([PY, "manage.py", "migrate"], check=True)
print("      OK")

# Init forfaits
print("\n[BONUS] Initialisation des 5 forfaits...")
subprocess.run([PY, "manage.py", "shell", "-c",
    "from abonnements.models import init_forfaits; init_forfaits(); print('5 forfaits crees')"
], check=True)

print("\n" + "="*65)
print("  SYSTEME D'ABONNEMENT INSTALLE !")
print("="*65)
print(f"\nRelancer le serveur :")
print(f"   {PY} manage.py runserver")
print(f"\n5 forfaits disponibles :")
print(f"  - FREEMIUM   : Gratuit (7 jours)")
print(f"  - STARTER    : 25 000 FCFA / mois")
print(f"  - PRO        : 60 000 FCFA / mois (populaire)")
print(f"  - ENTERPRISE : 120 000 FCFA / mois")
print(f"  - ANNUEL     : 300 000 FCFA / 12 mois")
print(f"\nA l'inscription : Freemium auto active 7 jours")
print(f"Page tarifs : /abonnements/tarifs/")
print(f"Mon abonnement : /abonnements/mon-abonnement/")
print(f"Admin paiements : /abonnements/admin/paiements/")
print("="*65 + "\n")