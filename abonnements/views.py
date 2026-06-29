from django.shortcuts import render, redirect, get_object_or_404
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
        message=f'Votre abonnement est actif jusqu\'au {abo.date_fin.strftime("%d/%m/%Y")}',
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
    paiement.notes += f"\nRefuse par {request.user.get_full_name()} le {timezone.now()}"
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
        nb_abonnes=Count('abonnement', filter=__import__('django').db.models.Q(abonnement__statut='ACTIF'))
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
