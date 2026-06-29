"""
Calcul des etats financiers SYSCOHADA
"""
from django.db.models import Sum, Q
from comptabilite.models import Ecriture

def calcul_bilan(entreprise, exercice=None):
    """Calcule le bilan (Actif/Passif) selon SYSCOHADA"""
    ecritures = Ecriture.objects.filter(entreprise=entreprise)
    if exercice:
        ecritures = ecritures.filter(date_ecriture__year=exercice)

    # ACTIF
    actif = {
        'immobilisations': {
            'terrains': solde_compte(ecritures, '211'),
            'batiments': solde_compte(ecritures, '213'),
            'materiel': solde_compte(ecritures, '244'),
            'transport': solde_compte(ecritures, '245'),
        },
        'creances': {
            'clients': solde_compte(ecritures, '411'),
        },
        'tresorerie': {
            'banque': solde_compte(ecritures, '521'),
            'caisse': solde_compte(ecritures, '531'),
        },
    }

    # PASSIF
    passif = {
        'capitaux': {
            'capital': solde_compte(ecritures, '101', sens='credit'),
            'reserves': solde_compte(ecritures, '106', sens='credit'),
        },
        'dettes': {
            'fournisseurs': solde_compte(ecritures, '401', sens='credit'),
            'personnel': solde_compte(ecritures, '421', sens='credit'),
            'tva': solde_compte(ecritures, '443', sens='credit'),
        },
    }

    # Totaux
    total_actif = sum_dict(actif)
    total_passif = sum_dict(passif)

    return {
        'actif': actif,
        'passif': passif,
        'total_actif': total_actif,
        'total_passif': total_passif,
    }


def calcul_compte_resultat(entreprise, exercice=None):
    """Calcule le compte de resultat"""
    ecritures = Ecriture.objects.filter(entreprise=entreprise)
    if exercice:
        ecritures = ecritures.filter(date_ecriture__year=exercice)

    # CHARGES (Classe 6)
    charges = {
        '601_achats': solde_compte(ecritures, '601'),
        '605_autres_achats': solde_compte(ecritures, '605'),
        '622_locations': solde_compte(ecritures, '622'),
        '624_entretien': solde_compte(ecritures, '624'),
        '626_telecom': solde_compte(ecritures, '626'),
        '631_personnel': solde_compte(ecritures, '631'),
        '641_impots': solde_compte(ecritures, '641'),
    }
    total_charges = sum(charges.values())

    # PRODUITS (Classe 7)
    produits = {
        '701_ventes': solde_compte(ecritures, '701', sens='credit'),
        '706_services': solde_compte(ecritures, '706', sens='credit'),
        '707_accessoires': solde_compte(ecritures, '707', sens='credit'),
    }
    total_produits = sum(produits.values())

    resultat = total_produits - total_charges

    return {
        'charges': charges,
        'produits': produits,
        'total_charges': total_charges,
        'total_produits': total_produits,
        'resultat': resultat,
    }


def solde_compte(ecritures, numero, sens='debit'):
    """Calcule le solde d'un compte"""
    if sens == 'debit':
        return float(ecritures.filter(compte_debit__numero=numero).aggregate(s=Sum('montant'))['s'] or 0)
    else:
        return float(ecritures.filter(compte_credit__numero=numero).aggregate(s=Sum('montant'))['s'] or 0)


def sum_dict(d):
    total = 0
    for k, v in d.items():
        if isinstance(v, dict):
            total += sum_dict(v)
        else:
            total += v
    return total


def grand_livre(entreprise, exercice=None):
    """Retourne toutes les ecritures pour le grand livre"""
    ecritures = Ecriture.objects.filter(entreprise=entreprise).order_by('date_ecriture', 'id')
    if exercice:
        ecritures = ecritures.filter(date_ecriture__year=exercice)
    return ecritures
