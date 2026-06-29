"""
COMPTAAUTO - Pack 2 Admin Avance
- Configuration plateforme (forfaits, parametres)
- Coupons / Codes promo
- Newsletter / Emails en masse
- Statistiques avancees (churn, LTV, retention)
- Rapports PDF automatiques
- Backup base de donnees
Usage: python add_admin_pack2.py
"""
import os, sys, subprocess
from pathlib import Path

BASE = Path(__file__).parent

print("\n" + "="*65)
print("  PACK 2 : ADMIN AVANCE")
print("="*65 + "\n")

if os.name == 'nt':
    PY = str(BASE / "venv" / "Scripts" / "python.exe")
else:
    PY = str(BASE / "venv" / "bin" / "python")

print("[1/3] Generation des fichiers...")
FILES = {}

# ============================================
# AJOUT MODELES dans admin_panel/models.py
# ============================================
FILES["admin_panel/models_extra.py"] = '''"""
Modeles supplementaires Pack 2
"""
from django.db import models
from django.utils import timezone
from accounts.models import User, Entreprise


class ParametreSysteme(models.Model):
    """Parametres globaux de la plateforme"""
    cle = models.CharField(max_length=100, unique=True)
    valeur = models.TextField()
    description = models.TextField(blank=True)
    type_valeur = models.CharField(max_length=20, default='TEXT',
        choices=[('TEXT', 'Texte'), ('NUMBER', 'Nombre'), ('BOOLEAN', 'Booleen'), ('JSON', 'JSON')])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'parametres_systeme'

    def __str__(self):
        return self.cle


class CouponPromo(models.Model):
    """Codes promo / coupons"""
    TYPES_REDUCTION = [
        ('POURCENTAGE', 'Pourcentage'),
        ('MONTANT', 'Montant fixe'),
        ('JOURS_GRATUITS', 'Jours gratuits'),
    ]

    code = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=200)
    type_reduction = models.CharField(max_length=20, choices=TYPES_REDUCTION, default='POURCENTAGE')
    valeur = models.DecimalField(max_digits=10, decimal_places=2)
    date_debut = models.DateField()
    date_fin = models.DateField()
    max_utilisations = models.IntegerField(default=100)
    nb_utilisations = models.IntegerField(default=0)
    actif = models.BooleanField(default=True)
    forfaits_eligibles = models.ManyToManyField('abonnements.Forfait', blank=True,
        help_text="Vide = tous les forfaits")
    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coupons_promo'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.valeur}{'%' if self.type_reduction == 'POURCENTAGE' else 'F'}"

    @property
    def est_valide(self):
        today = timezone.now().date()
        return (self.actif and
                self.date_debut <= today <= self.date_fin and
                self.nb_utilisations < self.max_utilisations)


class UtilisationCoupon(models.Model):
    """Historique d'utilisation des coupons"""
    coupon = models.ForeignKey(CouponPromo, on_delete=models.CASCADE, related_name='utilisations')
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE)
    paiement = models.ForeignKey('abonnements.Paiement', on_delete=models.CASCADE, null=True)
    reduction_appliquee = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'utilisations_coupons'


class CampagneEmail(models.Model):
    """Campagnes email aux entreprises"""
    STATUTS = [
        ('BROUILLON', 'Brouillon'),
        ('PROGRAMMEE', 'Programmee'),
        ('ENVOYEE', 'Envoyee'),
        ('ANNULEE', 'Annulee'),
    ]

    nom = models.CharField(max_length=200)
    sujet = models.CharField(max_length=200)
    contenu = models.TextField()

    # Ciblage
    cible_toutes = models.BooleanField(default=True)
    cible_actives = models.BooleanField(default=True, help_text="Uniquement entreprises avec abonnement actif")
    cible_forfaits = models.ManyToManyField('abonnements.Forfait', blank=True)
    entreprises_destinataires = models.ManyToManyField(Entreprise, blank=True, related_name='campagnes_recues')

    statut = models.CharField(max_length=20, choices=STATUTS, default='BROUILLON')
    nb_destinataires = models.IntegerField(default=0)
    nb_envoyes = models.IntegerField(default=0)
    date_envoi_prevue = models.DateTimeField(null=True, blank=True)
    date_envoi_effective = models.DateTimeField(null=True, blank=True)

    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'campagnes_email'
        ordering = ['-created_at']

    def __str__(self):
        return self.nom


class RapportMensuel(models.Model):
    """Rapports mensuels generes"""
    mois = models.IntegerField()
    annee = models.IntegerField()
    fichier_pdf = models.FileField(upload_to='rapports/%Y/', null=True, blank=True)

    # Donnees du rapport
    revenus_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    nb_nouveaux_clients = models.IntegerField(default=0)
    nb_abonnements_actifs = models.IntegerField(default=0)
    nb_paiements = models.IntegerField(default=0)
    mrr = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    churn_rate = models.FloatField(default=0)

    genere_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rapports_mensuels'
        unique_together = ('mois', 'annee')
        ordering = ['-annee', '-mois']

    def __str__(self):
        return f"Rapport {self.mois}/{self.annee}"


class BackupBase(models.Model):
    """Backups de la base de donnees"""
    nom = models.CharField(max_length=200)
    fichier = models.FileField(upload_to='backups/')
    taille_mo = models.FloatField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'backups_base'
        ordering = ['-created_at']
'''

# ============================================
# VUES PACK 2
# ============================================
FILES["admin_panel/views_pack2.py"] = '''"""Vues Pack 2 - Admin avance"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta, datetime
from django.conf import settings
import os, json, shutil

from accounts.models import User, Entreprise
from abonnements.models import Forfait, Abonnement, Paiement
from comptabilite.models import Ecriture
from .models_extra import (ParametreSysteme, CouponPromo, UtilisationCoupon,
                            CampagneEmail, RapportMensuel, BackupBase)
from .utils import log_action


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_super_admin:
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================
# CONFIGURATION PLATEFORME
# ============================================
@admin_required
def config_plateforme(request):
    """Page de configuration generale"""
    if request.method == 'POST':
        for cle, valeur in request.POST.items():
            if cle.startswith('param_'):
                key = cle.replace('param_', '')
                ParametreSysteme.objects.update_or_create(
                    cle=key, defaults={'valeur': valeur}
                )
        messages.success(request, "Parametres mis a jour")
        return redirect('admin_config_plateforme')

    init_parametres_defaut()
    parametres = ParametreSysteme.objects.all()
    return render(request, 'admin_panel/config_plateforme.html', {'parametres': parametres})


def init_parametres_defaut():
    """Initialise les parametres par defaut"""
    defaults = [
        ('NOM_PLATEFORME', 'ComptaAuto', 'Nom de la plateforme'),
        ('EMAIL_SUPPORT', 'support@comptaauto.ci', 'Email du support'),
        ('TELEPHONE_SUPPORT', '+225 0707 12 34 56', 'Telephone du support'),
        ('DEVISE_DEFAUT', 'FCFA', 'Devise par defaut'),
        ('FUSEAU_HORAIRE', 'Africa/Abidjan', 'Fuseau horaire'),
        ('NOTIFICATIONS_EMAIL', 'true', 'Activer notifications email'),
        ('MAINTENANCE_MODE', 'false', 'Mode maintenance'),
        ('MESSAGE_MAINTENANCE', '', 'Message de maintenance'),
    ]
    for cle, val, desc in defaults:
        ParametreSysteme.objects.get_or_create(cle=cle, defaults={'valeur': val, 'description': desc})


@admin_required
def gestion_forfaits(request):
    """Modifier les forfaits"""
    forfaits = Forfait.objects.all().order_by('ordre')
    return render(request, 'admin_panel/gestion_forfaits.html', {'forfaits': forfaits})


@admin_required
def modifier_forfait(request, pk):
    """Modifier un forfait"""
    forfait = get_object_or_404(Forfait, pk=pk)
    if request.method == 'POST':
        forfait.nom = request.POST.get('nom', forfait.nom)
        forfait.prix = float(request.POST.get('prix', forfait.prix))
        forfait.duree_jours = int(request.POST.get('duree_jours', forfait.duree_jours))
        forfait.description = request.POST.get('description', forfait.description)
        forfait.max_factures_ocr_mois = int(request.POST.get('max_factures_ocr_mois', 10))
        forfait.max_utilisateurs = int(request.POST.get('max_utilisateurs', 1))
        forfait.max_ecritures_mois = int(request.POST.get('max_ecritures_mois', 50))
        forfait.rapprochement_bancaire = request.POST.get('rapprochement_bancaire') == 'on'
        forfait.reporting_avance = request.POST.get('reporting_avance') == 'on'
        forfait.support_prioritaire = request.POST.get('support_prioritaire') == 'on'
        forfait.export_illimite = request.POST.get('export_illimite') == 'on'
        forfait.couleur = request.POST.get('couleur', forfait.couleur)
        forfait.actif = request.POST.get('actif') == 'on'
        forfait.populaire = request.POST.get('populaire') == 'on'
        forfait.save()
        log_action(request, 'MODIFICATION', f"Modification forfait {forfait.nom}", forfait)
        messages.success(request, "Forfait modifie")
        return redirect('admin_gestion_forfaits')
    return render(request, 'admin_panel/forfait_form.html', {'forfait': forfait})


# ============================================
# COUPONS / PROMO
# ============================================
@admin_required
def coupons_list(request):
    coupons = CouponPromo.objects.all()
    return render(request, 'admin_panel/coupons_list.html', {'coupons': coupons})


@admin_required
def coupon_create(request):
    if request.method == 'POST':
        try:
            c = CouponPromo.objects.create(
                code=request.POST.get('code').upper(),
                description=request.POST.get('description'),
                type_reduction=request.POST.get('type_reduction', 'POURCENTAGE'),
                valeur=float(request.POST.get('valeur', 0)),
                date_debut=request.POST.get('date_debut'),
                date_fin=request.POST.get('date_fin'),
                max_utilisations=int(request.POST.get('max_utilisations', 100)),
                actif=request.POST.get('actif') == 'on',
                cree_par=request.user,
            )
            log_action(request, 'CREATION', f"Coupon {c.code} cree", c)
            messages.success(request, f"Coupon {c.code} cree")
            return redirect('admin_coupons_list')
        except Exception as e:
            messages.error(request, f"Erreur: {e}")

    forfaits = Forfait.objects.filter(actif=True)
    return render(request, 'admin_panel/coupon_form.html', {'coupon': None, 'forfaits': forfaits})


@admin_required
def coupon_delete(request, pk):
    c = get_object_or_404(CouponPromo, pk=pk)
    code = c.code
    c.delete()
    log_action(request, 'SUPPRESSION', f"Coupon {code} supprime")
    return JsonResponse({'status': 'ok'})


@admin_required
def coupon_toggle(request, pk):
    c = get_object_or_404(CouponPromo, pk=pk)
    c.actif = not c.actif
    c.save()
    return JsonResponse({'status': 'ok', 'actif': c.actif})


# ============================================
# CAMPAGNES EMAIL / NEWSLETTER
# ============================================
@admin_required
def campagnes_list(request):
    campagnes = CampagneEmail.objects.all()
    return render(request, 'admin_panel/campagnes_list.html', {'campagnes': campagnes})


@admin_required
def campagne_create(request):
    if request.method == 'POST':
        c = CampagneEmail.objects.create(
            nom=request.POST.get('nom'),
            sujet=request.POST.get('sujet'),
            contenu=request.POST.get('contenu'),
            cible_toutes=request.POST.get('cible_toutes') == 'on',
            cible_actives=request.POST.get('cible_actives') == 'on',
            cree_par=request.user,
        )

        # Calculer destinataires
        if c.cible_toutes:
            destinataires = Entreprise.objects.all()
        else:
            destinataires = Entreprise.objects.filter(abonnements__statut='ACTIF').distinct()

        if c.cible_actives:
            destinataires = destinataires.filter(statut='ACTIF')

        c.nb_destinataires = destinataires.count()
        c.save()

        messages.success(request, f"Campagne creee. {c.nb_destinataires} destinataires.")
        return redirect('admin_campagne_detail', pk=c.pk)
    return render(request, 'admin_panel/campagne_form.html')


@admin_required
def campagne_detail(request, pk):
    c = get_object_or_404(CampagneEmail, pk=pk)
    return render(request, 'admin_panel/campagne_detail.html', {'campagne': c})


@admin_required
def campagne_envoyer(request, pk):
    """Envoie la campagne (creation notifications in-app)"""
    c = get_object_or_404(CampagneEmail, pk=pk)
    if c.statut == 'ENVOYEE':
        return JsonResponse({'error': 'Deja envoyee'}, status=400)

    # Destinataires
    if c.cible_toutes:
        destinataires = Entreprise.objects.all()
    else:
        destinataires = Entreprise.objects.filter(abonnements__statut='ACTIF').distinct()

    if c.cible_actives:
        destinataires = destinataires.filter(statut='ACTIF')

    # Creer notifications
    from communication.models import Notification
    nb = 0
    for ent in destinataires:
        Notification.objects.create(
            user=ent.responsable, type_notif='ANNONCE',
            titre=c.sujet, message=c.contenu[:200],
            lien='/communication/notifications/',
        )
        nb += 1

    c.statut = 'ENVOYEE'
    c.nb_envoyes = nb
    c.date_envoi_effective = timezone.now()
    c.save()

    log_action(request, 'AUTRE', f"Campagne '{c.nom}' envoyee a {nb} destinataires", c)
    return JsonResponse({'status': 'ok', 'nb': nb})


# ============================================
# STATISTIQUES AVANCEES
# ============================================
@admin_required
def stats_avancees(request):
    """Page stats avancees : churn, LTV, retention"""
    now = timezone.now()
    debut_mois = now.replace(day=1, hour=0, minute=0, second=0)

    # Churn rate (taux d'abonnements expires ce mois / actifs debut mois)
    actifs_debut = Abonnement.objects.filter(
        date_debut__lt=debut_mois, statut='ACTIF'
    ).count()
    expires_mois = Abonnement.objects.filter(
        statut='EXPIRE', date_fin__gte=debut_mois, date_fin__lt=now
    ).count()
    churn_rate = (expires_mois / actifs_debut * 100) if actifs_debut > 0 else 0

    # LTV (Lifetime Value moyen)
    total_revenu = float(Paiement.objects.filter(statut='VALIDE').aggregate(s=Sum('montant'))['s'] or 0)
    nb_clients = Entreprise.objects.count()
    ltv = total_revenu / nb_clients if nb_clients > 0 else 0

    # Taux de retention (clients > 30 jours)
    clients_30j = Entreprise.objects.filter(
        date_inscription__lt=now - timedelta(days=30)
    ).count()
    clients_retenus = Entreprise.objects.filter(
        date_inscription__lt=now - timedelta(days=30),
        abonnements__statut='ACTIF',
    ).distinct().count()
    retention_rate = (clients_retenus / clients_30j * 100) if clients_30j > 0 else 0

    # Taux de conversion Freemium -> Payant
    freemium = Abonnement.objects.filter(forfait__code='FREEMIUM').values('entreprise').distinct().count()
    payants = Abonnement.objects.filter(forfait__prix__gt=0).values('entreprise').distinct().count()
    conversion_rate = (payants / freemium * 100) if freemium > 0 else 0

    # Top forfaits (par revenus)
    top_forfaits = []
    for f in Forfait.objects.all():
        rev = float(Paiement.objects.filter(forfait=f, statut='VALIDE').aggregate(s=Sum('montant'))['s'] or 0)
        nb = Paiement.objects.filter(forfait=f, statut='VALIDE').count()
        if nb > 0:
            top_forfaits.append({'forfait': f, 'revenus': rev, 'nb_ventes': nb})
    top_forfaits.sort(key=lambda x: x['revenus'], reverse=True)

    # Utilisation OCR par entreprise
    from ocr_app.models import FactureOCR
    top_ocr = Entreprise.objects.annotate(
        nb_ocr=Count('factures')
    ).filter(nb_ocr__gt=0).order_by('-nb_ocr')[:10]

    return render(request, 'admin_panel/stats_avancees.html', {
        'churn_rate': round(churn_rate, 2),
        'ltv': round(ltv, 2),
        'retention_rate': round(retention_rate, 2),
        'conversion_rate': round(conversion_rate, 2),
        'top_forfaits': top_forfaits,
        'top_ocr': top_ocr,
        'expires_mois': expires_mois,
        'nb_clients': nb_clients,
    })


# ============================================
# RAPPORTS MENSUELS
# ============================================
@admin_required
def rapports_list(request):
    rapports = RapportMensuel.objects.all()
    return render(request, 'admin_panel/rapports_list.html', {'rapports': rapports})


@admin_required
def generer_rapport_mensuel(request):
    """Genere le rapport du mois en cours"""
    now = timezone.now()
    mois = int(request.POST.get('mois', now.month))
    annee = int(request.POST.get('annee', now.year))

    debut_mois = datetime(annee, mois, 1)
    if mois == 12:
        fin_mois = datetime(annee+1, 1, 1)
    else:
        fin_mois = datetime(annee, mois+1, 1)

    # Calculs
    paiements = Paiement.objects.filter(
        statut='VALIDE', created_at__gte=debut_mois, created_at__lt=fin_mois
    )
    revenus = float(paiements.aggregate(s=Sum('montant'))['s'] or 0)
    nouveaux = Entreprise.objects.filter(
        date_inscription__gte=debut_mois, date_inscription__lt=fin_mois
    ).count()
    actifs = Abonnement.objects.filter(statut='ACTIF').count()

    # MRR
    mrr = 0
    for abo in Abonnement.objects.filter(statut='ACTIF'):
        if abo.forfait.duree_jours <= 31:
            mrr += float(abo.forfait.prix)
        else:
            mrr += float(abo.forfait.prix) * 30 / abo.forfait.duree_jours

    # Generer PDF
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from io import BytesIO
    from django.core.files.base import ContentFile

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    mois_noms = ['Janvier','Fevrier','Mars','Avril','Mai','Juin','Juillet','Aout','Septembre','Octobre','Novembre','Decembre']

    elements.append(Paragraph(f"<b>RAPPORT MENSUEL</b>", styles['Title']))
    elements.append(Paragraph(f"<b>ComptaAuto - {mois_noms[mois-1]} {annee}</b>", styles['Heading2']))
    elements.append(Spacer(1, 30))

    data = [
        ['Indicateur', 'Valeur'],
        ['Revenus du mois', f'{revenus:,.0f} FCFA'],
        ['Nouveaux clients', f'{nouveaux}'],
        ['Abonnements actifs', f'{actifs}'],
        ['Nombre de paiements', f'{paiements.count()}'],
        ['MRR (Revenu Mensuel Recurrent)', f'{int(mrr):,} FCFA'],
        ['ARR (Revenu Annuel Recurrent)', f'{int(mrr*12):,} FCFA'],
    ]
    t = Table(data, colWidths=[300, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#14706b')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 10),
        ('FONTNAME', (0,1), (0,-1), 'Helvetica-Bold'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 30))

    # Top forfaits du mois
    elements.append(Paragraph("<b>Repartition par forfait</b>", styles['Heading3']))
    forfait_data = [['Forfait', 'Ventes', 'Revenus']]
    for f in Forfait.objects.all():
        p_forfait = paiements.filter(forfait=f)
        if p_forfait.count() > 0:
            rev = float(p_forfait.aggregate(s=Sum('montant'))['s'] or 0)
            forfait_data.append([f.nom, str(p_forfait.count()), f'{rev:,.0f} F'])
    t2 = Table(forfait_data, colWidths=[250, 100, 150])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#14706b')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t2)

    elements.append(Spacer(1, 50))
    elements.append(Paragraph(f"<i>Rapport genere le {now.strftime('%d/%m/%Y %H:%M')} par {request.user.get_full_name()}</i>", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)

    # Sauvegarder
    rapport, created = RapportMensuel.objects.update_or_create(
        mois=mois, annee=annee,
        defaults={
            'revenus_total': revenus,
            'nb_nouveaux_clients': nouveaux,
            'nb_abonnements_actifs': actifs,
            'nb_paiements': paiements.count(),
            'mrr': mrr,
            'genere_par': request.user,
        }
    )
    rapport.fichier_pdf.save(
        f'rapport_{mois:02d}_{annee}.pdf',
        ContentFile(buffer.getvalue()),
        save=True,
    )

    log_action(request, 'CREATION', f"Rapport mensuel {mois}/{annee} genere", rapport)
    messages.success(request, f"Rapport {mois_noms[mois-1]} {annee} genere !")
    return redirect('admin_rapports_list')


# ============================================
# BACKUP BASE DE DONNEES
# ============================================
@admin_required
def backups_list(request):
    backups = BackupBase.objects.all()
    return render(request, 'admin_panel/backups_list.html', {'backups': backups})


@admin_required
def creer_backup(request):
    """Cree un backup de la base SQLite"""
    try:
        from django.core.files.base import ContentFile
        from django.conf import settings

        db_path = settings.DATABASES['default']['NAME']

        if not os.path.exists(db_path):
            messages.error(request, "Base de donnees introuvable")
            return redirect('admin_backups_list')

        # Lire le fichier
        with open(db_path, 'rb') as f:
            content = f.read()

        taille_mo = len(content) / (1024 * 1024)
        nom = f"backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}.sqlite3"

        backup = BackupBase.objects.create(
            nom=nom, taille_mo=round(taille_mo, 2), created_by=request.user,
        )
        backup.fichier.save(nom, ContentFile(content), save=True)

        log_action(request, 'CREATION', f"Backup base de donnees ({taille_mo:.2f} Mo)", backup)
        messages.success(request, f"Backup cree : {nom} ({taille_mo:.2f} Mo)")
    except Exception as e:
        messages.error(request, f"Erreur: {e}")

    return redirect('admin_backups_list')


@admin_required
def telecharger_backup(request, pk):
    backup = get_object_or_404(BackupBase, pk=pk)
    log_action(request, 'EXPORT', f"Telechargement backup {backup.nom}", backup)
    return FileResponse(backup.fichier.open('rb'), as_attachment=True, filename=backup.nom)


@admin_required
def supprimer_backup(request, pk):
    backup = get_object_or_404(BackupBase, pk=pk)
    nom = backup.nom
    if backup.fichier:
        try: backup.fichier.delete()
        except: pass
    backup.delete()
    log_action(request, 'SUPPRESSION', f"Backup {nom} supprime")
    return JsonResponse({'status': 'ok'})
'''

# ============================================
# URLS PACK 2
# ============================================
FILES["admin_panel/urls_pack2.py"] = '''from django.urls import path
from . import views_pack2

urlpatterns = [
    # Configuration
    path('config/', views_pack2.config_plateforme, name='admin_config_plateforme'),
    path('forfaits/', views_pack2.gestion_forfaits, name='admin_gestion_forfaits'),
    path('forfaits/<int:pk>/edit/', views_pack2.modifier_forfait, name='admin_modifier_forfait'),

    # Coupons
    path('coupons/', views_pack2.coupons_list, name='admin_coupons_list'),
    path('coupons/create/', views_pack2.coupon_create, name='admin_coupon_create'),
    path('coupons/<int:pk>/delete/', views_pack2.coupon_delete, name='admin_coupon_delete'),
    path('coupons/<int:pk>/toggle/', views_pack2.coupon_toggle, name='admin_coupon_toggle'),

    # Campagnes
    path('campagnes/', views_pack2.campagnes_list, name='admin_campagnes_list'),
    path('campagnes/create/', views_pack2.campagne_create, name='admin_campagne_create'),
    path('campagnes/<int:pk>/', views_pack2.campagne_detail, name='admin_campagne_detail'),
    path('campagnes/<int:pk>/envoyer/', views_pack2.campagne_envoyer, name='admin_campagne_envoyer'),

    # Stats avancees
    path('stats-avancees/', views_pack2.stats_avancees, name='admin_stats_avancees'),

    # Rapports
    path('rapports/', views_pack2.rapports_list, name='admin_rapports_list'),
    path('rapports/generer/', views_pack2.generer_rapport_mensuel, name='admin_generer_rapport'),

    # Backups
    path('backups/', views_pack2.backups_list, name='admin_backups_list'),
    path('backups/creer/', views_pack2.creer_backup, name='admin_creer_backup'),
    path('backups/<int:pk>/telecharger/', views_pack2.telecharger_backup, name='admin_telecharger_backup'),
    path('backups/<int:pk>/delete/', views_pack2.supprimer_backup, name='admin_supprimer_backup'),
]
'''

# ============================================
# UPDATE admin_panel/urls.py pour inclure pack2
# ============================================
FILES["admin_panel/urls.py"] = '''from django.urls import path, include
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard_admin, name='admin_dashboard'),
    path('api/stats/', views.stats_data, name='admin_stats_data'),

    # Utilisateurs
    path('users/', views.users_list, name='admin_users_list'),
    path('users/create/', views.user_create, name='admin_user_create'),
    path('users/<int:pk>/', views.user_detail, name='admin_user_detail'),
    path('users/<int:pk>/edit/', views.user_edit, name='admin_user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='admin_user_delete'),
    path('users/<int:pk>/reset-password/', views.user_reset_password, name='admin_user_reset_password'),
    path('users/<int:pk>/toggle-active/', views.user_toggle_active, name='admin_user_toggle_active'),
    path('users/<int:pk>/impersonate/', views.user_impersonate, name='admin_user_impersonate'),
    path('stop-impersonate/', views.stop_impersonate, name='admin_stop_impersonate'),

    # Entreprises
    path('entreprises/', views.entreprises_list, name='admin_entreprises_list'),
    path('entreprises/<int:pk>/', views.entreprise_detail, name='admin_entreprise_detail'),
    path('entreprises/<int:pk>/edit/', views.entreprise_edit, name='admin_entreprise_edit'),
    path('entreprises/<int:pk>/note/', views.ajouter_note, name='admin_ajouter_note'),
    path('notes/<int:pk>/delete/', views.supprimer_note, name='admin_supprimer_note'),
    path('entreprises/<int:pk>/tag/', views.ajouter_tag_entreprise, name='admin_ajouter_tag_entreprise'),
    path('entreprise-tags/<int:pk>/delete/', views.retirer_tag_entreprise, name='admin_retirer_tag_entreprise'),

    # Tags
    path('tags/', views.tags_list, name='admin_tags_list'),
    path('tags/<int:pk>/delete/', views.tag_delete, name='admin_tag_delete'),

    # Finances
    path('finances/', views.finances_dashboard, name='admin_finances'),

    # Logs
    path('logs/', views.logs_list, name='admin_logs_list'),

    # Exports
    path('export/entreprises-csv/', views.export_entreprises_csv, name='admin_export_entreprises_csv'),
    path('export/paiements-excel/', views.export_paiements_excel, name='admin_export_paiements_excel'),

    # Pack 2
    path('pack2/', include('admin_panel.urls_pack2')),
]
'''

# ============================================
# TEMPLATES PACK 2
# ============================================

FILES["templates/admin_panel/config_plateforme.html"] = '''{% extends 'admin_panel/base_admin.html' %}{% block page_title %}Configuration plateforme{% endblock %}{% block content %}
<div class="card"><div class="card-body">
<h5>Parametres globaux</h5>
<form method="POST">{% csrf_token %}
{% for p in parametres %}
<div class="mb-3">
<label><strong>{{ p.cle }}</strong> {% if p.description %}<small class="text-muted">- {{ p.description }}</small>{% endif %}</label>
{% if p.type_valeur == 'BOOLEAN' %}
<select name="param_{{ p.cle }}" class="form-select"><option value="true" {% if p.valeur == 'true' %}selected{% endif %}>Oui</option><option value="false" {% if p.valeur == 'false' %}selected{% endif %}>Non</option></select>
{% elif p.type_valeur == 'NUMBER' %}
<input type="number" name="param_{{ p.cle }}" class="form-control" value="{{ p.valeur }}">
{% else %}
<input type="text" name="param_{{ p.cle }}" class="form-control" value="{{ p.valeur }}">
{% endif %}
</div>
{% endfor %}
<button type="submit" class="btn btn-primary"><i class="bi bi-check"></i> Sauvegarder</button>
</form>
</div></div>
{% endblock %}
'''

FILES["templates/admin_panel/gestion_forfaits.html"] = '''{% extends 'admin_panel/base_admin.html' %}{% block page_title %}Gestion des forfaits{% endblock %}{% block content %}
<div class="row g-3">
{% for f in forfaits %}
<div class="col-md-4"><div class="card" style="border-top: 4px solid {{ f.couleur }};"><div class="card-body">
<i class="bi {{ f.icone }}" style="font-size:2.5rem;color:{{ f.couleur }};"></i>
<h4>{{ f.nom }}</h4>
{% if f.populaire %}<span class="badge bg-primary">POPULAIRE</span>{% endif %}
{% if not f.actif %}<span class="badge bg-secondary">DESACTIVE</span>{% endif %}
<h2 class="mt-3">{{ f.prix|floatformat:0 }} F</h2>
<p class="text-muted">{{ f.duree_jours }} jours</p>
<hr>
<small>
<i class="bi bi-file-earmark"></i> {{ f.max_factures_ocr_mois }} OCR/mois<br>
<i class="bi bi-people"></i> {{ f.max_utilisateurs }} utilisateurs<br>
<i class="bi bi-journal-text"></i> {{ f.max_ecritures_mois }} ecritures/mois<br>
</small>
<a href="{% url 'admin_modifier_forfait' f.pk %}" class="btn btn-primary btn-sm mt-3 w-100"><i class="bi bi-pencil"></i> Modifier</a>
</div></div></div>
{% endfor %}
</div>
{% endblock %}
'''

FILES["templates/admin_panel/forfait_form.html"] = '''{% extends 'admin_panel/base_admin.html' %}{% block page_title %}Modifier {{ forfait.nom }}{% endblock %}{% block content %}
<a href="{% url 'admin_gestion_forfaits' %}" class="btn btn-link"><i class="bi bi-arrow-left"></i> Retour</a>
<div class="card mt-3"><div class="card-body">
<form method="POST">{% csrf_token %}
<div class="row">
<div class="col-md-6 mb-3"><label>Nom</label><input type="text" name="nom" class="form-control" value="{{ forfait.nom }}" required></div>
<div class="col-md-3 mb-3"><label>Prix (FCFA)</label><input type="number" name="prix" class="form-control" value="{{ forfait.prix }}" step="100" required></div>
<div class="col-md-3 mb-3"><label>Duree (jours)</label><input type="number" name="duree_jours" class="form-control" value="{{ forfait.duree_jours }}" required></div>
<div class="col-12 mb-3"><label>Description</label><textarea name="description" class="form-control" rows="2">{{ forfait.description }}</textarea></div>
<div class="col-md-4 mb-3"><label>Max factures OCR/mois</label><input type="number" name="max_factures_ocr_mois" class="form-control" value="{{ forfait.max_factures_ocr_mois }}"></div>
<div class="col-md-4 mb-3"><label>Max utilisateurs</label><input type="number" name="max_utilisateurs" class="form-control" value="{{ forfait.max_utilisateurs }}"></div>
<div class="col-md-4 mb-3"><label>Max ecritures/mois</label><input type="number" name="max_ecritures_mois" class="form-control" value="{{ forfait.max_ecritures_mois }}"></div>
<div class="col-md-3 mb-3"><label><input type="checkbox" name="rapprochement_bancaire" {% if forfait.rapprochement_bancaire %}checked{% endif %}> Rapprochement</label></div>
<div class="col-md-3 mb-3"><label><input type="checkbox" name="reporting_avance" {% if forfait.reporting_avance %}checked{% endif %}> Reporting avance</label></div>
<div class="col-md-3 mb-3"><label><input type="checkbox" name="support_prioritaire" {% if forfait.support_prioritaire %}checked{% endif %}> Support prio</label></div>
<div class="col-md-3 mb-3"><label><input type="checkbox" name="export_illimite" {% if forfait.export_illimite %}checked{% endif %}> Export illimite</label></div>
<div class="col-md-4 mb-3"><label>Couleur</label><input type="color" name="couleur" class="form-control" value="{{ forfait.couleur }}"></div>
<div class="col-md-4 mb-3"><label><input type="checkbox" name="actif" {% if forfait.actif %}checked{% endif %}> Forfait actif</label></div>
<div class="col-md-4 mb-3"><label><input type="checkbox" name="populaire" {% if forfait.populaire %}checked{% endif %}> Marquer "Populaire"</label></div>
</div>
<button type="submit" class="btn btn-primary"><i class="bi bi-check"></i> Sauvegarder</button>
</form>
</div></div>
{% endblock %}
'''

FILES["templates/admin_panel/coupons_list.html"] = '''{% extends 'admin_panel/base_admin.html' %}{% block page_title %}Coupons promo{% endblock %}{% block content %}
<div class="d-flex justify-content-end mb-3"><a href="{% url 'admin_coupon_create' %}" class="btn btn-primary"><i class="bi bi-plus"></i> Nouveau coupon</a></div>
<div class="card"><div class="card-body">
<table class="table">
<thead><tr><th>Code</th><th>Description</th><th>Reduction</th><th>Periode</th><th>Utilisations</th><th>Statut</th><th>Actions</th></tr></thead>
<tbody>
{% for c in coupons %}
<tr>
<td><strong style="font-family:monospace;background:#f4b860;color:white;padding:4px 8px;border-radius:4px;">{{ c.code }}</strong></td>
<td>{{ c.description }}</td>
<td>{% if c.type_reduction == 'POURCENTAGE' %}-{{ c.valeur|floatformat:0 }}%{% elif c.type_reduction == 'MONTANT' %}-{{ c.valeur|floatformat:0 }} F{% else %}+{{ c.valeur|floatformat:0 }} jours{% endif %}</td>
<td><small>{{ c.date_debut|date:"d/m/Y" }} - {{ c.date_fin|date:"d/m/Y" }}</small></td>
<td>{{ c.nb_utilisations }}/{{ c.max_utilisations }}</td>
<td>{% if c.est_valide %}<span class="badge bg-success">Actif</span>{% else %}<span class="badge bg-secondary">Inactif</span>{% endif %}</td>
<td>
<button class="btn btn-sm btn-outline-secondary" onclick="toggle({{ c.pk }})"><i class="bi bi-{% if c.actif %}toggle-on{% else %}toggle-off{% endif %}"></i></button>
<button class="btn btn-sm btn-outline-danger" onclick="del({{ c.pk }})"><i class="bi bi-trash"></i></button>
</td>
</tr>
{% empty %}<tr><td colspan="7" class="text-center text-muted">Aucun coupon</td></tr>{% endfor %}
</tbody></table>
</div></div>
<script>
function getCookie(n){const v=`; ${document.cookie}`.split(`; ${n}=`);if(v.length===2)return v.pop().split(';').shift();}
async function toggle(id){await fetch('/admin-panel/pack2/coupons/'+id+'/toggle/',{method:'POST',headers:{'X-CSRFToken':getCookie('csrftoken')}});location.reload();}
async function del(id){if(!confirm('Supprimer ?'))return;await fetch('/admin-panel/pack2/coupons/'+id+'/delete/',{method:'POST',headers:{'X-CSRFToken':getCookie('csrftoken')}});location.reload();}
</script>
{% endblock %}
'''

FILES["templates/admin_panel/coupon_form.html"] = '''{% extends 'admin_panel/base_admin.html' %}{% block page_title %}Nouveau coupon{% endblock %}{% block content %}
<div class="card"><div class="card-body">
<form method="POST">{% csrf_token %}
<div class="row">
<div class="col-md-4 mb-3"><label>Code (en majuscules)</label><input type="text" name="code" class="form-control" placeholder="Ex: PROMO2026" required style="text-transform:uppercase;"></div>
<div class="col-md-8 mb-3"><label>Description</label><input type="text" name="description" class="form-control" placeholder="Ex: Promotion lancement" required></div>
<div class="col-md-4 mb-3"><label>Type de reduction</label><select name="type_reduction" class="form-select"><option value="POURCENTAGE">Pourcentage (%)</option><option value="MONTANT">Montant fixe (FCFA)</option><option value="JOURS_GRATUITS">Jours gratuits</option></select></div>
<div class="col-md-4 mb-3"><label>Valeur</label><input type="number" name="valeur" class="form-control" step="0.01" required></div>
<div class="col-md-4 mb-3"><label>Max utilisations</label><input type="number" name="max_utilisations" class="form-control" value="100"></div>
<div class="col-md-6 mb-3"><label>Date debut</label><input type="date" name="date_debut" class="form-control" required></div>
<div class="col-md-6 mb-3"><label>Date fin</label><input type="date" name="date_fin" class="form-control" required></div>
<div class="col-12 mb-3"><label><input type="checkbox" name="actif" checked> Activer immediatement</label></div>
</div>
<button type="submit" class="btn btn-primary"><i class="bi bi-check"></i> Creer</button>
<a href="{% url 'admin_coupons_list' %}" class="btn btn-secondary">Annuler</a>
</form>
</div></div>
{% endblock %}
'''

FILES["templates/admin_panel/campagnes_list.html"] = '''{% extends 'admin_panel/base_admin.html' %}{% block page_title %}Campagnes Email{% endblock %}{% block content %}
<div class="d-flex justify-content-end mb-3"><a href="{% url 'admin_campagne_create' %}" class="btn btn-primary"><i class="bi bi-plus"></i> Nouvelle campagne</a></div>
<div class="card"><div class="card-body">
<table class="table">
<thead><tr><th>Nom</th><th>Sujet</th><th>Destinataires</th><th>Envoyes</th><th>Statut</th><th>Date</th><th></th></tr></thead>
<tbody>
{% for c in campagnes %}
<tr>
<td><strong>{{ c.nom }}</strong></td>
<td>{{ c.sujet }}</td>
<td>{{ c.nb_destinataires }}</td>
<td>{{ c.nb_envoyes }}</td>
<td><span class="badge bg-{% if c.statut == 'ENVOYEE' %}success{% elif c.statut == 'BROUILLON' %}secondary{% else %}warning{% endif %}">{{ c.get_statut_display }}</span></td>
<td>{{ c.created_at|date:"d/m/Y" }}</td>
<td><a href="{% url 'admin_campagne_detail' c.pk %}" class="btn btn-sm btn-outline-primary"><i class="bi bi-eye"></i></a></td>
</tr>
{% empty %}<tr><td colspan="7" class="text-center text-muted">Aucune campagne</td></tr>{% endfor %}
</tbody></table>
</div></div>
{% endblock %}
'''

FILES["templates/admin_panel/campagne_form.html"] = '''{% extends 'admin_panel/base_admin.html' %}{% block page_title %}Nouvelle campagne email{% endblock %}{% block content %}
<div class="card"><div class="card-body">
<form method="POST">{% csrf_token %}
<div class="mb-3"><label>Nom de la campagne (interne)</label><input type="text" name="nom" class="form-control" required></div>
<div class="mb-3"><label>Sujet</label><input type="text" name="sujet" class="form-control" required></div>
<div class="mb-3"><label>Contenu du message</label><textarea name="contenu" class="form-control" rows="8" required></textarea></div>
<div class="mb-3">
<label><input type="checkbox" name="cible_toutes" checked> Cibler toutes les entreprises</label><br>
<label><input type="checkbox" name="cible_actives" checked> Uniquement entreprises actives (avec abonnement)</label>
</div>
<button type="submit" class="btn btn-primary"><i class="bi bi-check"></i> Creer (brouillon)</button>
<a href="{% url 'admin_campagnes_list' %}" class="btn btn-secondary">Annuler</a>
</form>
</div></div>
{% endblock %}
'''

FILES["templates/admin_panel/campagne_detail.html"] = '''{% extends 'admin_panel/base_admin.html' %}{% block page_title %}{{ campagne.nom }}{% endblock %}{% block content %}
<a href="{% url 'admin_campagnes_list' %}" class="btn btn-link"><i class="bi bi-arrow-left"></i> Retour</a>
<div class="card mt-3"><div class="card-body">
<div class="row">
<div class="col-md-8">
<h4>{{ campagne.sujet }}</h4>
<p class="text-muted">Cree par {{ campagne.cree_par.email }} le {{ campagne.created_at|date:"d/m/Y H:i" }}</p>
<div class="border p-3 rounded bg-light">{{ campagne.contenu|linebreaks }}</div>
</div>
<div class="col-md-4">
<div class="border p-3 rounded">
<p><strong>Statut :</strong> <span class="badge bg-{% if campagne.statut == 'ENVOYEE' %}success{% else %}secondary{% endif %}">{{ campagne.get_statut_display }}</span></p>
<p><strong>Destinataires :</strong> {{ campagne.nb_destinataires }}</p>
<p><strong>Envoyes :</strong> {{ campagne.nb_envoyes }}</p>
{% if campagne.date_envoi_effective %}<p><strong>Date envoi :</strong> {{ campagne.date_envoi_effective|date:"d/m/Y H:i" }}</p>{% endif %}
{% if campagne.statut == 'BROUILLON' %}
<button class="btn btn-success w-100" onclick="envoyer({{ campagne.pk }})"><i class="bi bi-send"></i> Envoyer maintenant</button>
{% endif %}
</div>
</div>
</div>
</div></div>
<script>
function getCookie(n){const v=`; ${document.cookie}`.split(`; ${n}=`);if(v.length===2)return v.pop().split(';').shift();}
async function envoyer(id){if(!confirm('Envoyer cette campagne ?'))return;const r=await fetch('/admin-panel/pack2/campagnes/'+id+'/envoyer/',{method:'POST',headers:{'X-CSRFToken':getCookie('csrftoken')}});const j=await r.json();if(r.ok){alert('Envoyee a '+j.nb+' destinataires');location.reload();}else alert('Erreur');}
</script>
{% endblock %}
'''

FILES["templates/admin_panel/stats_avancees.html"] = '''{% extends 'admin_panel/base_admin.html' %}{% block page_title %}Statistiques avancees{% endblock %}{% block content %}

<div class="row g-3 mb-4">
<div class="col-md-3"><div class="metric-card"><div class="metric-label">CHURN RATE</div><div class="metric-value text-danger">{{ churn_rate }}%</div><small class="text-muted">{{ expires_mois }} abos expires ce mois</small></div></div>
<div class="col-md-3"><div class="metric-card" style="border-left-color:#1a8b85;"><div class="metric-label">LTV moyen</div><div class="metric-value">{{ ltv|floatformat:0 }} F</div><small class="text-muted">Revenu moyen par client</small></div></div>
<div class="col-md-3"><div class="metric-card" style="border-left-color:#28a745;"><div class="metric-label">RETENTION</div><div class="metric-value text-success">{{ retention_rate }}%</div><small class="text-muted">Clients > 30 jours actifs</small></div></div>
<div class="col-md-3"><div class="metric-card" style="border-left-color:#f4b860;"><div class="metric-label">CONVERSION</div><div class="metric-value">{{ conversion_rate }}%</div><small class="text-muted">Freemium > Payant</small></div></div>
</div>

<div class="row g-3">
<div class="col-md-6"><div class="card"><div class="card-body">
<h5>Top forfaits par revenus</h5>
<table class="table">
<thead><tr><th>Forfait</th><th>Ventes</th><th>Revenus</th></tr></thead>
<tbody>
{% for f in top_forfaits %}<tr><td><strong style="color:{{ f.forfait.couleur }};">{{ f.forfait.nom }}</strong></td><td>{{ f.nb_ventes }}</td><td><strong>{{ f.revenus|floatformat:0 }} F</strong></td></tr>{% endfor %}
</tbody></table>
</div></div></div>

<div class="col-md-6"><div class="card"><div class="card-body">
<h5>Top 10 utilisateurs OCR</h5>
<table class="table">
<thead><tr><th>Entreprise</th><th>Nb OCR</th></tr></thead>
<tbody>
{% for e in top_ocr %}<tr><td>{{ e.nom }}</td><td><span class="badge bg-primary">{{ e.nb_ocr }}</span></td></tr>{% endfor %}
</tbody></table>
</div></div></div>
</div>

<div class="card mt-3"><div class="card-body">
<h5>Definitions</h5>
<ul>
<li><strong>Churn Rate</strong> : % de clients qui n'ont pas renouvele ce mois</li>
<li><strong>LTV (Lifetime Value)</strong> : Revenu moyen genere par client depuis son inscription</li>
<li><strong>Retention</strong> : % de clients toujours actifs apres 30 jours</li>
<li><strong>Conversion</strong> : % de Freemium qui sont passes payants</li>
</ul>
</div></div>

{% endblock %}
'''

FILES["templates/admin_panel/rapports_list.html"] = '''{% extends 'admin_panel/base_admin.html' %}{% block page_title %}Rapports mensuels{% endblock %}{% block content %}
<div class="card mb-3"><div class="card-body">
<h5>Generer un nouveau rapport</h5>
<form method="POST" action="{% url 'admin_generer_rapport' %}" class="d-flex gap-2">{% csrf_token %}
<select name="mois" class="form-select" style="width:150px;">
<option value="1">Janvier</option><option value="2">Fevrier</option><option value="3">Mars</option><option value="4">Avril</option><option value="5">Mai</option><option value="6">Juin</option><option value="7">Juillet</option><option value="8">Aout</option><option value="9">Septembre</option><option value="10">Octobre</option><option value="11">Novembre</option><option value="12">Decembre</option>
</select>
<input type="number" name="annee" class="form-control" value="2026" min="2024" max="2030" style="width:150px;">
<button type="submit" class="btn btn-primary"><i class="bi bi-file-earmark-pdf"></i> Generer le rapport PDF</button>
</form>
</div></div>

<div class="card"><div class="card-body">
<h5>Rapports existants</h5>
<table class="table">
<thead><tr><th>Mois</th><th>Revenus</th><th>Nouveaux clients</th><th>Abonnements actifs</th><th>MRR</th><th>Genere le</th><th>PDF</th></tr></thead>
<tbody>
{% for r in rapports %}
<tr>
<td><strong>{{ r.mois }}/{{ r.annee }}</strong></td>
<td>{{ r.revenus_total|floatformat:0 }} F</td>
<td>{{ r.nb_nouveaux_clients }}</td>
<td>{{ r.nb_abonnements_actifs }}</td>
<td>{{ r.mrr|floatformat:0 }} F</td>
<td>{{ r.created_at|date:"d/m/Y H:i" }}</td>
<td>{% if r.fichier_pdf %}<a href="{{ r.fichier_pdf.url }}" class="btn btn-sm btn-outline-primary" target="_blank"><i class="bi bi-download"></i> Telecharger</a>{% endif %}</td>
</tr>
{% empty %}<tr><td colspan="7" class="text-center text-muted">Aucun rapport</td></tr>{% endfor %}
</tbody></table>
</div></div>
{% endblock %}
'''

FILES["templates/admin_panel/backups_list.html"] = '''{% extends 'admin_panel/base_admin.html' %}{% block page_title %}Backups base de donnees{% endblock %}{% block content %}
<div class="card mb-3 border-warning"><div class="card-body">
<h5><i class="bi bi-exclamation-triangle"></i> Important</h5>
<p>Sauvegardez regulierement votre base de donnees. En cas de probleme, vous pourrez restaurer un backup.</p>
<form method="POST" action="{% url 'admin_creer_backup' %}">{% csrf_token %}
<button type="submit" class="btn btn-warning"><i class="bi bi-cloud-arrow-down"></i> Creer un backup maintenant</button>
</form>
</div></div>

<div class="card"><div class="card-body">
<h5>Backups existants</h5>
<table class="table">
<thead><tr><th>Nom</th><th>Taille</th><th>Cree par</th><th>Date</th><th>Actions</th></tr></thead>
<tbody>
{% for b in backups %}
<tr>
<td><strong>{{ b.nom }}</strong></td>
<td>{{ b.taille_mo }} Mo</td>
<td>{{ b.created_by.email|default:"-" }}</td>
<td>{{ b.created_at|date:"d/m/Y H:i" }}</td>
<td>
<a href="{% url 'admin_telecharger_backup' b.pk %}" class="btn btn-sm btn-outline-primary"><i class="bi bi-download"></i></a>
<button class="btn btn-sm btn-outline-danger" onclick="del({{ b.pk }})"><i class="bi bi-trash"></i></button>
</td>
</tr>
{% empty %}<tr><td colspan="5" class="text-center text-muted">Aucun backup</td></tr>{% endfor %}
</tbody></table>
</div></div>
<script>
function getCookie(n){const v=`; ${document.cookie}`.split(`; ${n}=`);if(v.length===2)return v.pop().split(';').shift();}
async function del(id){if(!confirm('Supprimer ce backup ?'))return;await fetch('/admin-panel/pack2/backups/'+id+'/delete/',{method:'POST',headers:{'X-CSRFToken':getCookie('csrftoken')}});location.reload();}
</script>
{% endblock %}
'''

# ============================================
# UPDATE SIDEBAR ADMIN pour ajouter Pack 2
# ============================================
FILES["templates/admin_panel/base_admin.html"] = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{% block title %}Admin - ComptaAuto{% endblock %}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
{% load static %}
<link rel="stylesheet" href="{% static 'css/main.css' %}">
<style>
.admin-sidebar { width: 260px; background: #1a3e3a; color: white; min-height: 100vh; padding: 20px; position: fixed; left: 0; top: 0; overflow-y: auto; }
.admin-sidebar .brand-title { color: white; }
.admin-sidebar .nav-item { color: rgba(255,255,255,0.8); padding: 8px 12px; border-radius: 8px; text-decoration: none; display: flex; align-items: center; gap: 10px; margin-bottom: 2px; font-size: 0.9rem; }
.admin-sidebar .nav-item:hover { background: rgba(255,255,255,0.1); color: white; }
.admin-sidebar .nav-item.active { background: #14706b; color: white; }
.admin-sidebar .sidebar-section { font-size: 0.7rem; color: rgba(255,255,255,0.5); letter-spacing: 1.5px; margin: 15px 0 8px; }
.admin-main { margin-left: 260px; padding: 0; min-height: 100vh; background: #f5f7f7; }
.admin-topbar { background: white; padding: 15px 30px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
.admin-content { padding: 30px; }
.metric-card { background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 4px solid #14706b; }
.metric-value { font-size: 2rem; font-weight: 700; font-family: 'Playfair Display', serif; }
.metric-label { color: #6b8884; font-size: 0.85rem; }
</style>
</head>
<body>
<aside class="admin-sidebar">
<div class="logo-wrapper mb-4">
<div class="logo-icon" style="background:#f4b860;">C</div>
<div><h1 class="brand-title" style="color:white;font-size:1.3rem;">ComptaAuto</h1><p class="brand-subtitle" style="color:rgba(255,255,255,0.6);font-size:0.65rem;">CONSOLE ADMIN</p></div>
</div>

<div class="sidebar-section">PILOTAGE</div>
<nav>
<a href="{% url 'admin_dashboard' %}" class="nav-item {% if request.resolver_match.url_name == 'admin_dashboard' %}active{% endif %}"><i class="bi bi-grid-1x2"></i> Dashboard</a>
<a href="{% url 'admin_finances' %}" class="nav-item {% if 'finances' in request.path %}active{% endif %}"><i class="bi bi-currency-exchange"></i> Finances</a>
<a href="{% url 'admin_stats_avancees' %}" class="nav-item {% if 'stats-avancees' in request.path %}active{% endif %}"><i class="bi bi-graph-up-arrow"></i> Stats avancees</a>
</nav>

<div class="sidebar-section">GESTION</div>
<nav>
<a href="{% url 'admin_entreprises_list' %}" class="nav-item {% if 'entreprise' in request.path %}active{% endif %}"><i class="bi bi-building"></i> Entreprises</a>
<a href="{% url 'admin_users_list' %}" class="nav-item {% if 'users' in request.path %}active{% endif %}"><i class="bi bi-people"></i> Utilisateurs</a>
<a href="{% url 'admin_tags_list' %}" class="nav-item {% if 'tags' in request.path %}active{% endif %}"><i class="bi bi-tags"></i> Tags</a>
</nav>

<div class="sidebar-section">FACTURATION</div>
<nav>
<a href="{% url 'admin_paiements' %}" class="nav-item {% if 'paiements' in request.path %}active{% endif %}"><i class="bi bi-credit-card"></i> Paiements</a>
<a href="{% url 'admin_abonnements' %}" class="nav-item"><i class="bi bi-star"></i> Abonnements</a>
<a href="{% url 'admin_gestion_forfaits' %}" class="nav-item {% if 'forfaits' in request.path %}active{% endif %}"><i class="bi bi-box"></i> Forfaits</a>
<a href="{% url 'admin_coupons_list' %}" class="nav-item {% if 'coupons' in request.path %}active{% endif %}"><i class="bi bi-ticket"></i> Coupons promo</a>
</nav>

<div class="sidebar-section">COMMUNICATION</div>
<nav>
<a href="{% url 'tickets_list' %}" class="nav-item"><i class="bi bi-ticket-perforated"></i> Tickets</a>
<a href="{% url 'messagerie' %}" class="nav-item"><i class="bi bi-chat-dots"></i> Messages</a>
<a href="{% url 'rappels_list' %}" class="nav-item"><i class="bi bi-telephone"></i> Rappels</a>
<a href="{% url 'annonces_list' %}" class="nav-item"><i class="bi bi-megaphone"></i> Annonces</a>
<a href="{% url 'admin_campagnes_list' %}" class="nav-item {% if 'campagnes' in request.path %}active{% endif %}"><i class="bi bi-envelope-paper"></i> Campagnes email</a>
</nav>

<div class="sidebar-section">SYSTEME</div>
<nav>
<a href="{% url 'admin_config_plateforme' %}" class="nav-item {% if 'config' in request.path %}active{% endif %}"><i class="bi bi-sliders"></i> Configuration</a>
<a href="{% url 'admin_rapports_list' %}" class="nav-item {% if 'rapports' in request.path %}active{% endif %}"><i class="bi bi-file-earmark-pdf"></i> Rapports mensuels</a>
<a href="{% url 'admin_backups_list' %}" class="nav-item {% if 'backups' in request.path %}active{% endif %}"><i class="bi bi-cloud-arrow-down"></i> Backups</a>
<a href="{% url 'admin_logs_list' %}" class="nav-item {% if 'logs' in request.path %}active{% endif %}"><i class="bi bi-list-check"></i> Logs audit</a>
<a href="/django-admin/" class="nav-item" target="_blank"><i class="bi bi-gear"></i> Django Admin</a>
</nav>
</aside>

<main class="admin-main">
<header class="admin-topbar">
<div>
<h4 style="margin:0;font-family:'Playfair Display',serif;">{% block page_title %}Dashboard{% endblock %}</h4>
<small class="text-muted">{% block page_subtitle %}{% endblock %}</small>
</div>
<div class="d-flex align-items-center gap-3">
{% if request.session.admin_original_id %}
<a href="{% url 'admin_stop_impersonate' %}" class="btn btn-warning btn-sm"><i class="bi bi-arrow-left"></i> Revenir admin</a>
{% endif %}
<a href="{% url 'notifications_list' %}" style="color:#14706b;text-decoration:none;font-size:1.3rem;"><i class="bi bi-bell-fill"></i></a>
<div class="user-info"><div class="user-avatar" style="background:#1a3e3a;">{{ user.first_name.0|default:user.email.0|upper }}</div><div><strong>{{ user.get_full_name|default:user.email }}</strong><small>Super Admin</small></div></div>
<a href="{% url 'logout' %}" class="btn btn-outline-danger btn-sm">Deconnexion</a>
</div>
</header>

<div class="admin-content">
{% if messages %}{% for m in messages %}<div class="alert alert-{{ m.tags }} alert-dismissible fade show">{{ m }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>{% endfor %}{% endif %}
{% block content %}{% endblock %}
</div>
</main>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
{% block extra_js %}{% endblock %}
</body>
</html>
'''

# Ecriture
for fp, content in FILES.items():
    p = BASE / fp
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"      [OK] {fp}")

print(f"\n      {len(FILES)} fichiers crees/mis a jour\n")

# Update __init__.py de admin_panel pour importer models_extra
init_path = BASE / "admin_panel" / "__init__.py"
init_path.write_text("default_app_config = 'admin_panel.apps.AdminPanelConfig'\n", encoding='utf-8')

# Update models.py pour importer models_extra
models_path = BASE / "admin_panel" / "models.py"
current_models = models_path.read_text(encoding='utf-8')
if "from .models_extra import" not in current_models:
    current_models += "\n\n# Import models Pack 2\nfrom .models_extra import (ParametreSysteme, CouponPromo, UtilisationCoupon, CampagneEmail, RapportMensuel, BackupBase)\n"
    models_path.write_text(current_models, encoding='utf-8')

# Migrations
print("[2/3] Migrations base de donnees...")
subprocess.run([PY, "manage.py", "makemigrations", "admin_panel"], check=True)
subprocess.run([PY, "manage.py", "migrate"], check=True)
print("      OK")

# Init parametres
print("\n[3/3] Initialisation parametres systeme...")
subprocess.run([PY, "manage.py", "shell", "-c",
    "from admin_panel.views_pack2 import init_parametres_defaut; init_parametres_defaut(); print('Parametres OK')"
], check=True)

print("\n" + "="*65)
print("  PACK 2 ADMIN AVANCE INSTALLE !")
print("="*65)
print(f"\nRelancer le serveur :")
print(f"   {PY} manage.py runserver")
print(f"\nNouvelles fonctionnalites Pack 2 :")
print(f"  - Configuration plateforme : /admin-panel/pack2/config/")
print(f"  - Gestion forfaits         : /admin-panel/pack2/forfaits/")
print(f"  - Coupons promo            : /admin-panel/pack2/coupons/")
print(f"  - Campagnes email          : /admin-panel/pack2/campagnes/")
print(f"  - Stats avancees           : /admin-panel/pack2/stats-avancees/")
print(f"  - Rapports mensuels PDF    : /admin-panel/pack2/rapports/")
print(f"  - Backups BDD              : /admin-panel/pack2/backups/")
print(f"\nLa sidebar admin a ete enrichie avec ces nouvelles sections !")
print("="*65 + "\n")