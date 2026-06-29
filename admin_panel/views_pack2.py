"""Vues Pack 2 - Admin avance"""
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
