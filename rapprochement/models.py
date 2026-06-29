from django.db import models
from accounts.models import Entreprise
from comptabilite.models import Ecriture

class ReleveBancaire(models.Model):
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='releves')
    nom = models.CharField(max_length=200)
    banque = models.CharField(max_length=100, default='Banque')
    date_import = models.DateTimeField(auto_now_add=True)
    nb_operations = models.IntegerField(default=0)
    nb_rapprochees = models.IntegerField(default=0)
    class Meta:
        db_table = 'releves_bancaires'
        ordering = ['-date_import']
    def __str__(self):
        return f"{self.banque} - {self.nom}"

class OperationBancaire(models.Model):
    SENS = [('DEBIT', 'Debit'), ('CREDIT', 'Credit')]
    releve = models.ForeignKey(ReleveBancaire, on_delete=models.CASCADE, related_name='operations')
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE)
    date_operation = models.DateField()
    libelle = models.CharField(max_length=300)
    montant = models.DecimalField(max_digits=15, decimal_places=2)
    sens = models.CharField(max_length=10, choices=SENS, default='DEBIT')
    ecriture_associee = models.ForeignKey(Ecriture, null=True, blank=True, on_delete=models.SET_NULL, related_name='operations_rapprochees')
    score_rapprochement = models.FloatField(default=0.0)
    rapprochee = models.BooleanField(default=False)
    suggeree = models.BooleanField(default=False)
    class Meta:
        db_table = 'operations_bancaires'
        ordering = ['-date_operation']
    def __str__(self):
        return f"{self.date_operation} - {self.libelle} - {self.montant}"
