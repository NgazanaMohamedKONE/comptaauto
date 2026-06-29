from django.contrib import admin
from .models import FactureOCR
@admin.register(FactureOCR)
class FactureOCRAdmin(admin.ModelAdmin):
    list_display = ('nom_original','fournisseur','montant','statut','entreprise','created_at')
    list_filter = ('statut','entreprise')
