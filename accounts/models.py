from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        ENTREPRISE = 'ENTREPRISE', 'Entreprise'
    email = models.EmailField('Email', unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ENTREPRISE)
    telephone = models.CharField(max_length=20, blank=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    class Meta:
        db_table = 'users'
    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

class Entreprise(models.Model):
    class Formule(models.TextChoices):
        STARTER = 'STARTER', 'Starter'
        BUSINESS = 'BUSINESS', 'Business'
    class Statut(models.TextChoices):
        ACTIF = 'ACTIF', 'Actif'
        SUSPENDU = 'SUSPENDU', 'Suspendu'
    nom = models.CharField(max_length=200)
    secteur = models.CharField(max_length=100)
    adresse = models.TextField(blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    email_contact = models.EmailField()
    responsable = models.OneToOneField(User, on_delete=models.CASCADE, related_name='entreprise')
    formule = models.CharField(max_length=20, choices=Formule.choices, default=Formule.STARTER)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.ACTIF)
    exercice_courant = models.IntegerField(default=2026)
    devise = models.CharField(max_length=10, default='FCFA')
    date_inscription = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'entreprises'
        ordering = ['-date_inscription']
    def __str__(self):
        return self.nom
