"""
Verificateur d'alertes - lance les checks automatiquement
"""
from django.db.models import Sum
from comptabilite.models import Ecriture
from .models import Alerte, SeuilAlerte

def check_alertes(entreprise):
    """Verifie les seuils et cree les alertes"""
    nb_alertes = 0
    seuils = SeuilAlerte.objects.filter(entreprise=entreprise, actif=True)

    for seuil in seuils:
        if seuil.type_alerte == 'TRESORERIE_BASSE':
            tresorerie = Ecriture.objects.filter(
                entreprise=entreprise,
                compte_debit__numero__in=['521', '531']
            ).aggregate(s=Sum('montant'))['s'] or 0

            if tresorerie < seuil.seuil:
                if not Alerte.objects.filter(
                    entreprise=entreprise, titre='Tresorerie basse', lue=False
                ).exists():
                    Alerte.objects.create(
                        entreprise=entreprise, niveau='DANGER',
                        titre='Tresorerie basse',
                        message=f'Tresorerie actuelle : {tresorerie:,.0f} FCFA (seuil: {seuil.seuil:,.0f} FCFA)'
                    )
                    nb_alertes += 1

        elif seuil.type_alerte == 'CREANCE_ELEVEE':
            creances = Ecriture.objects.filter(
                entreprise=entreprise, compte_debit__numero='411'
            ).aggregate(s=Sum('montant'))['s'] or 0

            if creances > seuil.seuil:
                if not Alerte.objects.filter(
                    entreprise=entreprise, titre='Creances elevees', lue=False
                ).exists():
                    Alerte.objects.create(
                        entreprise=entreprise, niveau='WARNING',
                        titre='Creances elevees',
                        message=f'Creances clients : {creances:,.0f} FCFA (seuil: {seuil.seuil:,.0f} FCFA)'
                    )
                    nb_alertes += 1

    return nb_alertes


def init_seuils_par_defaut(entreprise):
    """Initialise les seuils par defaut"""
    defaults = [
        ('TRESORERIE_BASSE', 500000),
        ('CREANCE_ELEVEE', 2000000),
        ('DETTE_ELEVEE', 1000000),
    ]
    for type_a, seuil in defaults:
        SeuilAlerte.objects.get_or_create(
            entreprise=entreprise, type_alerte=type_a,
            defaults={'seuil': seuil}
        )
