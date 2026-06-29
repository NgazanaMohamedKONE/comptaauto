from django.contrib import admin
from .models import (Conversation, Message, Ticket, ReponseTicket,
                      Annonce, DemandeRappel, Notification)

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('entreprise', 'sujet', 'fermee', 'updated_at')
    list_filter = ('fermee',)

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('numero', 'entreprise', 'sujet', 'categorie', 'priorite', 'statut', 'created_at')
    list_filter = ('statut', 'priorite', 'categorie')

@admin.register(Annonce)
class AnnonceAdmin(admin.ModelAdmin):
    list_display = ('titre', 'type_annonce', 'cible_toutes', 'active', 'created_at')

@admin.register(DemandeRappel)
class DemandeRappelAdmin(admin.ModelAdmin):
    list_display = ('entreprise', 'sujet', 'date_souhaitee', 'creneau', 'statut')
    list_filter = ('statut', 'creneau')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type_notif', 'titre', 'lue', 'created_at')
    list_filter = ('type_notif', 'lue')
