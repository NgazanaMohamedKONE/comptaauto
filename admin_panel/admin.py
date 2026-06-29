from django.contrib import admin
from .models import LogAudit, NoteEntreprise, TagEntreprise, EntrepriseTag, SessionImpersonate

@admin.register(LogAudit)
class LogAuditAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'description', 'created_at')
    list_filter = ('action',)
    search_fields = ('description', 'user__email')

@admin.register(NoteEntreprise)
class NoteEntrepriseAdmin(admin.ModelAdmin):
    list_display = ('entreprise', 'auteur', 'importante', 'created_at')

@admin.register(TagEntreprise)
class TagEntrepriseAdmin(admin.ModelAdmin):
    list_display = ('nom', 'couleur')
