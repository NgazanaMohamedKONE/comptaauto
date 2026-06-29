"""
Algorithme de rapprochement bancaire
Score = Montant (0.5) + Date +/-3j (0.3) + Libelle Levenshtein (0.2)
"""
from datetime import timedelta
try:
    from Levenshtein import ratio as lev_ratio
except ImportError:
    def lev_ratio(a, b):
        # Fallback simple si Levenshtein pas installe
        a, b = a.lower(), b.lower()
        if not a or not b: return 0.0
        common = sum(1 for c in a if c in b)
        return common / max(len(a), len(b))

def calculate_score(operation, ecriture):
    """Calcule le score de rapprochement entre une operation bancaire et une ecriture"""
    score = 0.0

    # 1. Montant (poids 0.5)
    if abs(float(operation.montant) - float(ecriture.montant)) < 0.01:
        score += 0.5
    elif abs(float(operation.montant) - float(ecriture.montant)) / max(float(operation.montant), 1) < 0.05:
        score += 0.25  # Tolerance 5%

    # 2. Date +/- 3 jours (poids 0.3)
    delta = abs((operation.date_operation - ecriture.date_ecriture).days)
    if delta == 0:
        score += 0.3
    elif delta <= 3:
        score += 0.3 * (1 - delta / 4)

    # 3. Libelle Levenshtein (poids 0.2)
    sim = lev_ratio(operation.libelle.lower(), ecriture.libelle.lower())
    score += 0.2 * sim

    return round(score, 3)


def rapprocher_automatique(releve):
    """Lance le rapprochement automatique pour un releve"""
    from comptabilite.models import Ecriture
    from .models import OperationBancaire

    operations = OperationBancaire.objects.filter(releve=releve, rapprochee=False)
    ecritures = Ecriture.objects.filter(entreprise=releve.entreprise).exclude(
        operations_rapprochees__rapprochee=True
    )

    nb_auto = 0
    for op in operations:
        best_score = 0.0
        best_ec = None
        for ec in ecritures:
            score = calculate_score(op, ec)
            if score > best_score:
                best_score = score
                best_ec = ec

        if best_ec and best_score >= 0.85:
            op.ecriture_associee = best_ec
            op.score_rapprochement = best_score
            op.rapprochee = True
            op.save()
            nb_auto += 1
        elif best_ec and best_score >= 0.60:
            op.ecriture_associee = best_ec
            op.score_rapprochement = best_score
            op.suggeree = True
            op.save()

    releve.nb_rapprochees = nb_auto
    releve.save()
    return nb_auto
