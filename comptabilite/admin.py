from django.contrib import admin
from .models import Compte, Ecriture
@admin.register(Compte)
class CompteAdmin(admin.ModelAdmin):
    list_display = ('numero','libelle','entreprise','classe')
@admin.register(Ecriture)
class EcritureAdmin(admin.ModelAdmin):
    list_display = ('date_ecriture','libelle','montant','statut','entreprise')
    list_filter = ('statut','entreprise')
