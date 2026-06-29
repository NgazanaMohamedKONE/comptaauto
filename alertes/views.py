from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import SeuilAlerte, Alerte
from .checker import check_alertes, init_seuils_par_defaut

@login_required
def alertes_page(request):
    if not hasattr(request.user, 'entreprise'):
        return redirect('dashboard')

    # Init seuils par defaut si vide
    if not SeuilAlerte.objects.filter(entreprise=request.user.entreprise).exists():
        init_seuils_par_defaut(request.user.entreprise)

    # Lancer check
    check_alertes(request.user.entreprise)

    seuils = SeuilAlerte.objects.filter(entreprise=request.user.entreprise)
    alertes = Alerte.objects.filter(entreprise=request.user.entreprise)
    return render(request, 'alertes/index.html', {'seuils': seuils, 'alertes': alertes})

@login_required
def modifier_seuil(request, pk):
    seuil = get_object_or_404(SeuilAlerte, pk=pk, entreprise=request.user.entreprise)
    if request.method == 'POST':
        seuil.seuil = request.POST.get('seuil', seuil.seuil)
        seuil.actif = request.POST.get('actif') == 'on'
        seuil.notif_email = request.POST.get('notif_email') == 'on'
        seuil.save()
        messages.success(request, "Seuil modifie")
    return redirect('alertes_page')

@login_required
def marquer_lue(request, pk):
    a = get_object_or_404(Alerte, pk=pk, entreprise=request.user.entreprise)
    a.lue = True
    a.save()
    return JsonResponse({'status': 'ok'})
