from django.contrib import admin
from .models import ReleveBancaire, OperationBancaire

@admin.register(ReleveBancaire)
class ReleveBancaireAdmin(admin.ModelAdmin):
    list_display = ('nom', 'banque', 'entreprise', 'nb_operations', 'nb_rapprochees', 'date_import')

@admin.register(OperationBancaire)
class OperationBancaireAdmin(admin.ModelAdmin):
    list_display = ('date_operation', 'libelle', 'montant', 'sens', 'rapprochee', 'score_rapprochement')
    list_filter = ('rapprochee', 'sens')
