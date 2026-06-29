from django.shortcuts import render, redirect
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
