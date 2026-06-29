from django.db import models
from accounts.models import Entreprise

class SeuilAlerte(models.Model):
    TYPES = [
        ('TRESORERIE_BASSE', 'Tresorerie basse'),
        ('CREANCE_ELEVEE', 'Creances elevees'),
        ('DETTE_ELEVEE', 'Dettes elevees'),
        ('IMPAYE', 'Facture impayee'),
    ]
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='seuils')
    type_alerte = models.CharField(max_length=30, choices=TYPES)
    seuil = models.DecimalField(max_digits=15, decimal_places=2)
    actif = models.BooleanField(default=True)
    notif_email = models.BooleanField(default=True)
    class Meta:
        db_table = 'seuils_alertes'

class Alerte(models.Model):
    NIVEAUX = [('INFO', 'Info'), ('WARNING', 'Avertissement'), ('DANGER', 'Critique')]
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='alertes')
    niveau = models.CharField(max_length=20, choices=NIVEAUX, default='WARNING')
    titre = models.CharField(max_length=200)
    message = models.TextField()
    lue = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'alertes'
        ordering = ['-created_at']
