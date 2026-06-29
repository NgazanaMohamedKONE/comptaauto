from django.db import models
from accounts.models import Entreprise, User

class Compte(models.Model):
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='comptes')
    numero = models.CharField(max_length=10)
    libelle = models.CharField(max_length=200)
    classe = models.IntegerField()
    class Meta:
        db_table = 'comptes'
        unique_together = ('entreprise','numero')
        ordering = ['numero']
    def __str__(self):
        return f"{self.numero} - {self.libelle}"

class Ecriture(models.Model):
    class Statut(models.TextChoices):
        BROUILLON = 'BROUILLON', 'Brouillon'
        VALIDEE = 'VALIDEE', 'Validee'
        AUTO = 'AUTO', 'Auto (OCR)'
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='ecritures')
    date_ecriture = models.DateField()
    numero_piece = models.CharField(max_length=50, blank=True)
    libelle = models.CharField(max_length=300)
    compte_debit = models.ForeignKey(Compte, on_delete=models.PROTECT, related_name='ecritures_debit')
    compte_credit = models.ForeignKey(Compte, on_delete=models.PROTECT, related_name='ecritures_credit')
    montant = models.DecimalField(max_digits=15, decimal_places=2)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.BROUILLON)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'ecritures'
        ordering = ['-date_ecriture']
    def __str__(self):
        return f"{self.libelle} - {self.montant}"

PLAN_SYSCOHADA = {
    '101': ('Capital social',1), '401': ('Fournisseurs',4), '411': ('Clients',4),
    '521': ('Banque',5), '531': ('Caisse',5), '601': ('Achats marchandises',6),
    '605': ('Autres achats',6), '622': ('Locations',6), '626': ('Telecommunications',6),
    '631': ('Frais personnel',6), '701': ('Ventes',7), '706': ('Services',7),
}
