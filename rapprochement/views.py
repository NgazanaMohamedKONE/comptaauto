import csv, io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from datetime import datetime
from .models import ReleveBancaire, OperationBancaire
from .matcher import rapprocher_automatique

@login_required
def rapprochement_page(request):
    if not hasattr(request.user, 'entreprise'):
        return redirect('dashboard')
    releves = ReleveBancaire.objects.filter(entreprise=request.user.entreprise)
    return render(request, 'rapprochement/index.html', {'releves': releves})

@login_required
def import_releve(request):
    if request.method != 'POST' or not hasattr(request.user, 'entreprise'):
        return redirect('rapprochement_page')

    fichier = request.FILES.get('fichier')
    if not fichier:
        messages.error(request, "Fichier requis")
        return redirect('rapprochement_page')

    try:
        releve = ReleveBancaire.objects.create(
            entreprise=request.user.entreprise,
            nom=fichier.name,
            banque=request.POST.get('banque', 'Banque'),
        )

        # Parser CSV (format: date;libelle;montant;sens)
        decoded = fichier.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded), delimiter=';')

        nb = 0
        for row in reader:
            try:
                date_str = row.get('date', '').strip()
                date_op = None
                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                    try:
                        date_op = datetime.strptime(date_str, fmt).date()
                        break
                    except: pass
                if not date_op: continue

                OperationBancaire.objects.create(
                    releve=releve,
                    entreprise=request.user.entreprise,
                    date_operation=date_op,
                    libelle=row.get('libelle', '').strip()[:300],
                    montant=float(row.get('montant', '0').replace(',', '.').replace(' ', '')),
                    sens=row.get('sens', 'DEBIT').upper(),
                )
                nb += 1
            except Exception as e:
                print(f"Erreur ligne: {e}")
                continue

        releve.nb_operations = nb
        releve.save()

        # Lancer rapprochement automatique
        nb_auto = rapprocher_automatique(releve)
        messages.success(request, f"{nb} operations importees. {nb_auto} rapprochees automatiquement.")

    except Exception as e:
        messages.error(request, f"Erreur: {e}")

    return redirect('rapprochement_page')

@login_required
def detail_releve(request, pk):
    releve = get_object_or_404(ReleveBancaire, pk=pk, entreprise=request.user.entreprise)
    operations = releve.operations.all()
    return render(request, 'rapprochement/detail.html', {'releve': releve, 'operations': operations})

@login_required
def valider_rapprochement(request, op_id):
    op = get_object_or_404(OperationBancaire, pk=op_id, entreprise=request.user.entreprise)
    op.rapprochee = True
    op.suggeree = False
    op.save()
    return JsonResponse({'status': 'ok'})

@login_required
def telecharger_modele(request):
    """Telecharge un modele CSV"""
    from django.http import HttpResponse
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="modele_releve_bancaire.csv"'
    response.write('\ufeff')
    response.write('date;libelle;montant;sens\n')
    response.write('15/06/2026;Virement client ABC;500000;CREDIT\n')
    response.write('16/06/2026;Loyer juin 2026;280000;DEBIT\n')
    response.write('17/06/2026;Facture CIE;68000;DEBIT\n')
    return response
