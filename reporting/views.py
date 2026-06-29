from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .calculator import calcul_bilan, calcul_compte_resultat, grand_livre
from .exports import export_bilan_pdf, export_grand_livre_excel

@login_required
def reporting_index(request):
    if not hasattr(request.user, 'entreprise'):
        return redirect('dashboard')
    return render(request, 'reporting/index.html', {})

@login_required
def voir_bilan(request):
    if not hasattr(request.user, 'entreprise'):
        return redirect('dashboard')
    bilan = calcul_bilan(request.user.entreprise)
    return render(request, 'reporting/bilan.html', {'bilan': bilan})

@login_required
def voir_compte_resultat(request):
    if not hasattr(request.user, 'entreprise'):
        return redirect('dashboard')
    cr = calcul_compte_resultat(request.user.entreprise)
    return render(request, 'reporting/compte_resultat.html', {'cr': cr})

@login_required
def voir_grand_livre(request):
    if not hasattr(request.user, 'entreprise'):
        return redirect('dashboard')
    ecritures = grand_livre(request.user.entreprise)
    return render(request, 'reporting/grand_livre.html', {'ecritures': ecritures})

@login_required
def export_bilan(request):
    bilan = calcul_bilan(request.user.entreprise)
    buffer = export_bilan_pdf(bilan, request.user.entreprise)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="bilan_{request.user.entreprise.nom}.pdf"'
    return response

@login_required
def export_grand_livre(request):
    ecritures = grand_livre(request.user.entreprise)
    buffer = export_grand_livre_excel(ecritures, request.user.entreprise)
    response = HttpResponse(buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="grand_livre_{request.user.entreprise.nom}.xlsx"'
    return response
