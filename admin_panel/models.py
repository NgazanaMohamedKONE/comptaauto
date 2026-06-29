from django.db import models
from accounts.models import User, Entreprise


class LogAudit(models.Model):
    """Log de toutes les actions importantes"""
    ACTIONS = [
        ('CONNEXION', 'Connexion'),
        ('DECONNEXION', 'Deconnexion'),
        ('CREATION', 'Creation'),
        ('MODIFICATION', 'Modification'),
        ('SUPPRESSION', 'Suppression'),
        ('VALIDATION', 'Validation'),
        ('REFUS', 'Refus'),
        ('IMPERSONATE', 'Impersonification'),
        ('EXPORT', 'Export'),
        ('AUTRE', 'Autre'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='logs')
    action = models.CharField(max_length=20, choices=ACTIONS)
    objet_type = models.CharField(max_length=100, blank=True, help_text="Type d'objet (User, Entreprise, etc.)")
    objet_id = models.CharField(max_length=50, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'logs_audit'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.action} - {self.created_at}"


class NoteEntreprise(models.Model):
    """Notes internes sur une entreprise (par les admins)"""
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='notes_admin')
    auteur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    contenu = models.TextField()
    importante = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notes_entreprise'
        ordering = ['-created_at']


class TagEntreprise(models.Model):
    """Tags pour categoriser les entreprises (VIP, A surveiller, etc.)"""
    nom = models.CharField(max_length=50, unique=True)
    couleur = models.CharField(max_length=20, default='#14706b')
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'tags_entreprise'

    def __str__(self):
        return self.nom


class EntrepriseTag(models.Model):
    """Association entreprise <-> tag"""
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='tags')
    tag = models.ForeignKey(TagEntreprise, on_delete=models.CASCADE)
    ajoute_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'entreprise_tags'
        unique_together = ('entreprise', 'tag')


class SessionImpersonate(models.Model):
    """Trace les impersonifications"""
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='impersonations_faites')
    user_cible = models.ForeignKey(User, on_delete=models.CASCADE, related_name='impersonations_subies')
    raison = models.TextField()
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sessions_impersonate'


# Import models Pack 2
from .models_extra import (ParametreSysteme, CouponPromo, UtilisationCoupon, CampagneEmail, RapportMensuel, BackupBase)
