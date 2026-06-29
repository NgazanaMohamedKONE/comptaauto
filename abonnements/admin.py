from django.contrib import admin
from .models import Forfait, Abonnement, Paiement

@admin.register(Forfait)
class ForfaitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'prix', 'duree_jours', 'actif', 'populaire')
    list_filter = ('actif', 'populaire')

@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):
    list_display = ('entreprise', 'forfait', 'date_debut', 'date_fin', 'statut')
    list_filter = ('statut', 'forfait')

@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('reference', 'entreprise', 'forfait', 'montant', 'methode', 'statut', 'created_at')
    list_filter = ('statut', 'methode', 'forfait')
