from django.shortcuts import render, redirect
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
