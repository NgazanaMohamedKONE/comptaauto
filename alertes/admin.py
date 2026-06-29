from django.contrib import admin
from .models import SeuilAlerte, Alerte

@admin.register(SeuilAlerte)
class SeuilAlerteAdmin(admin.ModelAdmin):
    list_display = ('entreprise', 'type_alerte', 'seuil', 'actif')

@admin.register(Alerte)
class AlerteAdmin(admin.ModelAdmin):
    list_display = ('titre', 'niveau', 'entreprise', 'lue', 'created_at')
    list_filter = ('niveau', 'lue')
