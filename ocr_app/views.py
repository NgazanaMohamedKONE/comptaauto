from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from decimal import Decimal
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
        f.montant_original = result.get('montant_original')
        f.devise = result.get('devise', 'XOF')
        f.taux_change = result.get('taux_change', 1.0)
        f.date_facture = result['date_facture']
        f.compte_suggere = result['compte_suggere']
        f.libelle_suggere = result['libelle_suggere']
        f.score_confiance = result['score_confiance']
        f.statut = FactureOCR.Statut.TERMINE
        f.save()

        return JsonResponse({
            'id': f.id, 'status': 'ok',
            'fournisseur': f.fournisseur,
            'montant': str(f.montant) if f.montant else None,
            'montant_original': str(f.montant_original) if f.montant_original else None,
            'devise': f.devise,
            'taux_change': str(f.taux_change),
            'date': str(f.date_facture) if f.date_facture else None,
            'compte': f.compte_suggere,
            'libelle': f.libelle_suggere,
            'score': f.score_confiance,
        })
    except Exception as e:
        f.statut = FactureOCR.Statut.ERREUR
        f.save()
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_facture(request, pk):
    f = get_object_or_404(FactureOCR, pk=pk, entreprise=request.user.entreprise)
    return JsonResponse({
        'id': f.id, 'statut': f.statut,
        'fournisseur': f.fournisseur,
        'montant': str(f.montant) if f.montant else None,
        'montant_original': str(f.montant_original) if f.montant_original else None,
        'devise': f.devise,
        'devise_display': f.get_devise_display(),
        'taux_change': str(f.taux_change),
        'date_facture': str(f.date_facture) if f.date_facture else None,
        'compte_suggere': f.compte_suggere,
        'libelle_suggere': f.libelle_suggere,
        'texte_brut': f.texte_brut,
        'score_confiance': f.score_confiance,
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

        libelle_complet = f.libelle_suggere or f.fournisseur or 'Facture OCR'
        if f.devise != 'XOF' and f.montant_original:
            libelle_complet += f" ({f.montant_original} {f.devise})"

        Ecriture.objects.create(
            entreprise=request.user.entreprise,
            date_ecriture=f.date_facture or f.created_at.date(),
            numero_piece=f'FACT-{f.id}',
            libelle=libelle_complet,
            compte_debit=c_debit, compte_credit=c_credit,
            montant=f.montant,
            statut=Ecriture.Statut.AUTO,
            created_by=request.user)
        f.ecriture_creee = True
        f.save()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
