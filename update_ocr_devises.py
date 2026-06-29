"""
COMPTAAUTO - Mise a jour OCR multi-devises
- Detection automatique de la devise
- Conversion vers FCFA (devise reference)
Usage: python update_ocr_devises.py
"""
import os, sys, subprocess
from pathlib import Path

BASE = Path(__file__).parent

print("\n" + "="*65)
print("  MISE A JOUR OCR - Support Multi-Devises")
print("="*65 + "\n")

if os.name == 'nt':
    PY = str(BASE / "venv" / "Scripts" / "python.exe")
    PIP = str(BASE / "venv" / "Scripts" / "pip.exe")
else:
    PY = str(BASE / "venv" / "bin" / "python")
    PIP = str(BASE / "venv" / "bin" / "pip")

FILES = {}

# ============================================
# OCR SERVICE - Multi-devises
# ============================================
FILES["ocr_app/ocr_service.py"] = '''"""
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
    'XOF': [r'\\bfcfa\\b', r'\\bf\\s*cfa\\b', r'\\bxof\\b', r'\\bcfa\\b', r'francs?\\s*cfa', r'\\bf\\b(?!\\w)'],
    'EUR': [r'\\beur\\b', r'\\beuros?\\b', r'€'],
    'USD': [r'\\busd\\b', r'\\bdollars?\\s*us', r'\\bus\\$', r'\\$(?!\\w)'],
    'GBP': [r'\\bgbp\\b', r'\\bpounds?\\b', r'£', r'livres?\\s*sterling'],
    'MAD': [r'\\bmad\\b', r'dirhams?', r'\\bdh\\b'],
    'CAD': [r'\\bcad\\b', r'dollars?\\s*canadien'],
    'CNY': [r'\\bcny\\b', r'\\byuan', r'\\brmb\\b', r'¥'],
    'CHF': [r'\\bchf\\b', r'francs?\\s*suisse'],
    'JPY': [r'\\bjpy\\b', r'\\byens?\\b'],
    'NGN': [r'\\bngn\\b', r'nairas?', r'₦'],
    'GHS': [r'\\bghs\\b', r'cedis?'],
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
        r'(?:total|ttc|net\\s+a?\\s*payer|montant|sous[\\-\\s]?total|amount|due)\\s*[:=]?\\s*([\\d\\s.,]+)',
        # Avec devise apres : "185000 FCFA", "150 EUR", "$1,200"
        r'([\\d]{1,3}(?:[\\s.,]\\d{3})+(?:[.,]\\d{2})?)\\s*(?:fcfa|f\\b|cfa|xof|eur|euros?|€|usd|\\$|gbp|£|pounds?|mad|dh|cny|¥|chf)',
        # Format simple : "1234.56"
        r'([\\d]+[.,]\\d{2})',
    ]

    text_lower = text.lower()
    montants_trouves = []

    for pattern in patterns_montant:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        for m in matches:
            # Nettoyer le nombre
            clean = re.sub(r'[\\s]', '', m)
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
        r'(\\d{2}[/-]\\d{2}[/-]\\d{4})',
        r'(\\d{4}[/-]\\d{2}[/-]\\d{2})',
        r'(\\d{1,2}\\s+(?:jan|fev|fév|mar|avr|mai|juin|juil|aoû|aou|sep|oct|nov|déc|dec)\\w*\\s+\\d{4})',
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
    lines = [l.strip() for l in text.split('\\n') if l.strip()]
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
'''

# ============================================
# MODIFIER LE MODELE FactureOCR pour ajouter devise
# ============================================
FILES["ocr_app/models.py"] = '''from django.db import models
from accounts.models import Entreprise

class FactureOCR(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        TERMINE = 'TERMINE', 'Termine'
        ERREUR = 'ERREUR', 'Erreur'

    DEVISES = [
        ('XOF', 'FCFA (XOF)'),
        ('EUR', 'Euro (EUR)'),
        ('USD', 'Dollar US (USD)'),
        ('GBP', 'Livre Sterling (GBP)'),
        ('MAD', 'Dirham Marocain (MAD)'),
        ('CAD', 'Dollar Canadien (CAD)'),
        ('CNY', 'Yuan (CNY)'),
        ('CHF', 'Franc Suisse (CHF)'),
        ('JPY', 'Yen (JPY)'),
        ('NGN', 'Naira (NGN)'),
        ('GHS', 'Cedi (GHS)'),
    ]

    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='factures')
    fichier = models.FileField(upload_to='factures/%Y/%m/')
    nom_original = models.CharField(max_length=255)
    texte_brut = models.TextField(blank=True)
    fournisseur = models.CharField(max_length=200, blank=True)

    # Montants
    montant = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Montant en FCFA (converti)")
    montant_original = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Montant dans la devise d'origine")
    devise = models.CharField(max_length=10, choices=DEVISES, default='XOF')
    taux_change = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)

    date_facture = models.DateField(null=True, blank=True)
    compte_suggere = models.CharField(max_length=10, blank=True)
    libelle_suggere = models.CharField(max_length=200, blank=True)
    score_confiance = models.FloatField(default=0.0)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    ecriture_creee = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'factures_ocr'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nom_original} - {self.statut}"
'''

# ============================================
# UPDATE VIEWS pour exposer la devise
# ============================================
FILES["ocr_app/views.py"] = '''from django.shortcuts import render, redirect, get_object_or_404
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
'''

# ============================================
# UPDATE TEMPLATE OCR pour afficher la devise
# ============================================
FILES["templates/ocr/ocr_page.html"] = '''{% extends 'base.html' %}{% block title %}Saisie OCR{% endblock %}{% block page_title %}Saisie par OCR{% endblock %}{% block page_subtitle %}Extraction & categorisation automatique - Multi-devises{% endblock %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">
<div class="row g-4">
<div class="col-md-5">
<div class="upload-zone" onclick="document.getElementById('fileInput').click()">
<i class="bi bi-cloud-upload" style="font-size:3rem;color:#14706b;"></i>
<p class="mt-2"><strong>+ Importer une facture</strong></p>
<small class="text-muted">JPG, PNG, PDF</small>
<input type="file" id="fileInput" hidden accept="image/*,application/pdf">
</div>

<div class="mt-3 p-3" style="background:#f0f7f6;border-radius:8px;">
<small><strong>Devises supportees :</strong></small><br>
<small class="text-muted">FCFA, EUR, USD, GBP, MAD, CAD, CNY, CHF, JPY, NGN, GHS</small>
</div>

<h5 class="mt-4">Factures recentes</h5>
<div id="facturesList">
{% for f in factures %}
<div class="facture-card" onclick="loadFacture({{ f.id }})">
<i class="bi bi-file-earmark-text"></i>
<div class="flex-grow-1">
<strong>{{ f.nom_original }}</strong><br>
<small>
{{ f.fournisseur|default:'En attente' }} -
{% if f.montant_original and f.devise != 'XOF' %}
<strong>{{ f.montant_original|floatformat:2 }} {{ f.devise }}</strong>
<span class="text-muted">({{ f.montant|floatformat:0 }} FCFA)</span>
{% else %}
{{ f.montant|default:'0'|floatformat:0 }} FCFA
{% endif %}
- <span class="badge bg-{% if f.statut == 'TERMINE' %}success{% elif f.statut == 'ERREUR' %}danger{% else %}warning{% endif %}">{{ f.statut }}</span>
</small>
</div>
</div>
{% empty %}<p class="text-muted">Aucune facture.</p>{% endfor %}
</div>
</div>

<div class="col-md-7"><div class="card"><div class="card-body">
<h4>Saisie automatique par OCR</h4>
<p class="text-muted">De la piece scannee a l'ecriture comptable (toutes devises)</p>
<div id="resultatOCR">
<div class="text-center text-muted py-5">
<i class="bi bi-arrow-bar-up" style="font-size:3rem;"></i>
<p>Importez une facture pour lancer le traitement.</p>
</div>
</div>
</div></div></div>
</div>
</div></main></div>

<script>
const fileInput = document.getElementById('fileInput');
function getCookie(n){const v=`; ${document.cookie}`.split(`; ${n}=`);if(v.length===2)return v.pop().split(';').shift();}

fileInput.addEventListener('change', async(e) => {
    const file = e.target.files[0];
    if(!file) return;
    const fd = new FormData();
    fd.append('fichier', file);
    document.getElementById('resultatOCR').innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-3">Traitement OCR + detection devise...</p></div>';
    const r = await fetch('/ocr/upload/', {method:'POST', headers:{'X-CSRFToken':getCookie('csrftoken')}, body:fd});
    const j = await r.json();
    if(r.ok){
        setTimeout(()=>loadFacture(j.id),500);
        setTimeout(()=>location.reload(),3000);
    } else {
        document.getElementById('resultatOCR').innerHTML = '<div class="alert alert-danger">'+JSON.stringify(j)+'</div>';
    }
});

async function loadFacture(id){
    const r = await fetch('/ocr/facture/'+id+'/');
    const f = await r.json();
    if(f.statut === 'TERMINE'){
        let montantHtml = '';
        if(f.devise && f.devise !== 'XOF' && f.montant_original){
            montantHtml = `
                <tr><td><strong>Montant original</strong></td><td><span class="badge bg-info fs-6">${f.montant_original} ${f.devise}</span></td></tr>
                <tr><td><strong>Taux de change</strong></td><td>1 ${f.devise} = ${f.taux_change} FCFA</td></tr>
                <tr><td><strong>Montant converti</strong></td><td><strong style="color:#14706b;font-size:1.2em;">${parseInt(f.montant).toLocaleString()} FCFA</strong></td></tr>
            `;
        } else {
            montantHtml = `<tr><td><strong>Montant</strong></td><td><strong style="color:#14706b;font-size:1.2em;">${parseInt(f.montant).toLocaleString()} FCFA</strong></td></tr>`;
        }

        document.getElementById('resultatOCR').innerHTML = `
            <div class="alert alert-success"><i class="bi bi-check-circle"></i> Extraction OK - Devise detectee : <strong>${f.devise_display || f.devise}</strong></div>
            <table class="table">
                <tr><td><strong>Fournisseur</strong></td><td>${f.fournisseur||'-'}</td></tr>
                ${montantHtml}
                <tr><td><strong>Date</strong></td><td>${f.date_facture||'-'}</td></tr>
                <tr><td><strong>Compte suggere</strong></td><td><span class="badge bg-secondary">${f.compte_suggere||'-'}</span> ${f.libelle_suggere||''}</td></tr>
                <tr><td><strong>Confiance ML</strong></td><td><div class="progress" style="height:25px;"><div class="progress-bar bg-success" style="width:${(f.score_confiance*100).toFixed(0)}%">${(f.score_confiance*100).toFixed(0)}%</div></div></td></tr>
            </table>
            <details><summary class="text-muted">Texte brut extrait</summary><pre style="font-size:0.75rem;background:#f8f9fa;padding:10px;max-height:200px;overflow:auto;">${f.texte_brut||''}</pre></details>
            ${!f.ecriture_creee && f.montant ? `<button class="btn btn-connect w-100 mt-3" onclick="creerEcriture(${f.id})"><i class="bi bi-check2-circle"></i> Valider et creer l'ecriture comptable</button>` : '<div class="alert alert-info mt-3">Ecriture deja creee</div>'}
        `;
    } else if(f.statut === 'ERREUR'){
        document.getElementById('resultatOCR').innerHTML = '<div class="alert alert-danger">Erreur lors du traitement</div>';
    } else {
        setTimeout(()=>loadFacture(id), 1500);
    }
}

async function creerEcriture(id){
    const r = await fetch('/ocr/facture/'+id+'/creer-ecriture/', {method:'POST', headers:{'X-CSRFToken':getCookie('csrftoken')}});
    const j = await r.json();
    if(r.ok){
        alert('Ecriture creee avec succes !');
        location.reload();
    } else {
        alert('Erreur: '+JSON.stringify(j));
    }
}
</script>
{% endblock %}
'''

# Ecriture
print("[1/2] Mise a jour des fichiers...")
for fp, content in FILES.items():
    p = BASE / fp
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"      [OK] {fp}")

# Migrations
print("\n[2/2] Migrations base de donnees (ajout devise, montant_original, taux_change)...")
subprocess.run([PY, "manage.py", "makemigrations", "ocr_app"], check=True)
subprocess.run([PY, "manage.py", "migrate"], check=True)
print("      OK")

print("\n" + "="*65)
print("  OCR MULTI-DEVISES INSTALLE !")
print("="*65)
print(f"\nRelancer le serveur :")
print(f"   {PY} manage.py runserver")
print(f"\nDevises supportees :")
print(f"  - FCFA / XOF (taux : 1)")
print(f"  - EUR (taux : 1 EUR = 655.957 FCFA)")
print(f"  - USD (taux : 1 USD = 605 FCFA)")
print(f"  - GBP, MAD, CAD, CNY, CHF, JPY, NGN, GHS")
print(f"\nTestez avec une facture en EUR ou USD !")
print("="*65 + "\n")
