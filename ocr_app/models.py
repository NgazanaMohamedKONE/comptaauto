from django.db import models
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
