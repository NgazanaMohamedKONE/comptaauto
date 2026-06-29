"""
Service OCR avec support multi-devises
"""
import requests, re, os
from django.conf import settings
from decimal import Decimal

# ============ TAUX DE CHANGE (vers FCFA) ============
# Mis a jour : taux moyens 2026
TAUX_CHANGE_VERS_FCFA = {
    'XOF': 1.0,         # Franc CFA = devise reference
    'FCFA': 1.0,
    'EUR': 655.957,     # 1 EUR = 655.957 FCFA (taux fixe)
    'USD': 605.0,       # 1 USD ~ 605 FCFA
    'GBP': 765.0,       # 1 GBP ~ 765 FCFA
    'MAD': 60.5,        # 1 Dirham ~ 60 FCFA
    'CAD': 445.0,       # 1 CAD ~ 445 FCFA
    'CNY': 84.0,        # 1 Yuan ~ 84 FCFA
    'CHF': 685.0,       # 1 Franc Suisse ~ 685 FCFA
    'JPY': 4.0,         # 1 Yen ~ 4 FCFA
    'NGN': 0.7,         # 1 Naira ~ 0.7 FCFA
    'GHS': 50.0,        # 1 Cedi ~ 50 FCFA
}

# ============ PATTERNS DE DETECTION DEVISES ============
DEVISES_PATTERNS = {
    'XOF': [r'\bfcfa\b', r'\bf\s*cfa\b', r'\bxof\b', r'\bcfa\b', r'francs?\s*cfa', r'\bf\b(?!\w)'],
    'EUR': [r'\beur\b', r'\beuros?\b', r'€'],
    'USD': [r'\busd\b', r'\bdollars?\s*us', r'\bus\$', r'\$(?!\w)'],
    'GBP': [r'\bgbp\b', r'\bpounds?\b', r'£', r'livres?\s*sterling'],
    'MAD': [r'\bmad\b', r'dirhams?', r'\bdh\b'],
    'CAD': [r'\bcad\b', r'dollars?\s*canadien'],
    'CNY': [r'\bcny\b', r'\byuan', r'\brmb\b', r'¥'],
    'CHF': [r'\bchf\b', r'francs?\s*suisse'],
    'JPY': [r'\bjpy\b', r'\byens?\b'],
    'NGN': [r'\bngn\b', r'nairas?', r'₦'],
    'GHS': [r'\bghs\b', r'cedis?'],
}


def ocr_space_file(file_path, api_key=None):
    """Envoie un fichier a OCR.space API"""
    key = api_key or getattr(settings, 'OCR_SPACE_API_KEY', 'helloworld')
    with open(file_path, 'rb') as f:
        r = requests.post('https://api.ocr.space/parse/image',
            files={'filename': f},
            data={'apikey': key, 'language': 'fre', 'isOverlayRequired': False})
    j = r.json()
    if j.get('IsErroredOnProcessing'):
        raise Exception(j.get('ErrorMessage', 'Erreur OCR'))
    parsed = j.get('ParsedResults', [{}])[0]
    return parsed.get('ParsedText', '')


def detect_devise(text):
    """Detecte la devise utilisee dans le texte"""
    text_lower = text.lower()
    scores = {}

    for devise, patterns in DEVISES_PATTERNS.items():
        score = 0
        for p in patterns:
            matches = re.findall(p, text_lower)
            score += len(matches)
        if score > 0:
            scores[devise] = score

    if not scores:
        return 'XOF'  # Defaut : FCFA

    # Retourne la devise avec le plus d'occurrences
    return max(scores, key=scores.get)


def extract_montant_avec_devise(text):
    """
    Extrait le montant ET detecte la devise
    Retourne : (montant_original, devise, montant_fcfa)
    """
    devise = detect_devise(text)

    # Patterns pour montants (recherche large)
    patterns_montant = [
        # Avec mots cles : "Total : 185 000"
        r'(?:total|ttc|net\s+a?\s*payer|montant|sous[\-\s]?total|amount|due)\s*[:=]?\s*([\d\s.,]+)',
        # Avec devise apres : "185000 FCFA", "150 EUR", "$1,200"
        r'([\d]{1,3}(?:[\s.,]\d{3})+(?:[.,]\d{2})?)\s*(?:fcfa|f\b|cfa|xof|eur|euros?|€|usd|\$|gbp|£|pounds?|mad|dh|cny|¥|chf)',
        # Format simple : "1234.56"
        r'([\d]+[.,]\d{2})',
    ]

    text_lower = text.lower()
    montants_trouves = []

    for pattern in patterns_montant:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        for m in matches:
            # Nettoyer le nombre
            clean = re.sub(r'[\s]', '', m)
            # Gerer decimales : "1,234.56" ou "1.234,56"
            if ',' in clean and '.' in clean:
                if clean.rindex(',') > clean.rindex('.'):
                    # Format europeen : 1.234,56
                    clean = clean.replace('.', '').replace(',', '.')
                else:
                    # Format US : 1,234.56
                    clean = clean.replace(',', '')
            elif ',' in clean:
                # Si virgule isolee, peut etre decimale ou millier
                parts = clean.split(',')
                if len(parts[-1]) == 2:
                    # Decimale : "100,50"
                    clean = clean.replace(',', '.')
                else:
                    # Milliers : "100,000"
                    clean = clean.replace(',', '')

            try:
                val = float(clean)
                if val > 0 and val < 1e12:  # Sanity check
                    montants_trouves.append(val)
            except ValueError:
                continue

    if not montants_trouves:
        return None, devise, None

    # Prendre le plus grand (souvent le total)
    montant_original = max(montants_trouves)

    # Conversion vers FCFA
    taux = TAUX_CHANGE_VERS_FCFA.get(devise, 1.0)
    montant_fcfa = round(montant_original * taux, 2)

    return montant_original, devise, montant_fcfa


def extract_date(text):
    """Extrait la date de facture"""
    patterns = [
        r'(\d{2}[/-]\d{2}[/-]\d{4})',
        r'(\d{4}[/-]\d{2}[/-]\d{2})',
        r'(\d{1,2}\s+(?:jan|fev|fév|mar|avr|mai|juin|juil|aoû|aou|sep|oct|nov|déc|dec)\w*\s+\d{4})',
    ]
    from datetime import datetime
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            date_str = m.group(1)
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%Y-%m-%d']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except: pass
    return None


def extract_fournisseur(text):
    """Extrait le fournisseur (premiere ligne pertinente)"""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    # Ignorer les lignes trop courtes ou numeriques
    for line in lines:
        if len(line) > 3 and not line.replace(' ', '').isdigit():
            return line[:100]
    return lines[0][:100] if lines else ''


# ============ CATEGORISATION SYSCOHADA ============
REGLES_CATEGORISATION = {
    '626': ['orange', 'mtn', 'moov', 'telecom', 'internet', 'wifi', 'telephone', 'phone'],
    '605': ['cie', 'electricite', 'electricity', 'sodeci', 'eau', 'water', 'utility'],
    '622': ['loyer', 'location', 'rent', 'bail', 'immobilier'],
    '624': ['entretien', 'reparation', 'maintenance', 'service'],
    '625': ['assurance', 'insurance', 'nsia', 'saham'],
    '627': ['frais bancaire', 'commission banque', 'agios', 'bank fees'],
    '628': ['publicite', 'publicity', 'marketing', 'advertising'],
    '611': ['transport', 'taxi', 'carburant', 'essence', 'fuel', 'gas'],
    '601': ['achat', 'purchase', 'fourniture', 'supplies', 'marchandise'],
    '631': ['salaire', 'salary', 'paie', 'payroll', 'cnps', 'personnel'],
    '641': ['impot', 'tax', 'taxes'],
}


def categoriser(text):
    """Categorise le texte selon les regles SYSCOHADA"""
    text_lower = text.lower()
    for compte, mots in REGLES_CATEGORISATION.items():
        for mot in mots:
            if mot in text_lower:
                return compte, f'Categorisation auto ({mot})'
    return '605', 'Autres achats (defaut)'


def process_facture(file_path, api_key=None):
    """
    Pipeline complet OCR :
    1. Extraction texte (OCR.space)
    2. Detection devise + montant
    3. Conversion en FCFA
    4. Extraction date + fournisseur
    5. Categorisation SYSCOHADA
    """
    text = ocr_space_file(file_path, api_key)

    montant_original, devise, montant_fcfa = extract_montant_avec_devise(text)
    compte, libelle = categoriser(text)

    return {
        'texte_brut': text,
        'fournisseur': extract_fournisseur(text),
        'montant': montant_fcfa,
        'montant_original': montant_original,
        'devise': devise,
        'taux_change': TAUX_CHANGE_VERS_FCFA.get(devise, 1.0),
        'date_facture': extract_date(text),
        'compte_suggere': compte,
        'libelle_suggere': libelle,
        'score_confiance': 0.85 if compte != '605' else 0.55,
    }
