"""
COMPTAAUTO - Systeme de communication
- Messagerie interne (chat)
- Tickets support
- Annonces super admin
- Demandes de rappel
- Centre de notifications
Usage: python add_communication.py
"""
import os, sys, subprocess
from pathlib import Path

BASE = Path(__file__).parent

print("\n" + "="*65)
print("  AJOUT SYSTEME DE COMMUNICATION")
print("="*65 + "\n")

if os.name == 'nt':
    PY = str(BASE / "venv" / "Scripts" / "python.exe")
    PIP = str(BASE / "venv" / "Scripts" / "pip.exe")
else:
    PY = str(BASE / "venv" / "bin" / "python")
    PIP = str(BASE / "venv" / "bin" / "pip")

print("[1/3] Creation dossiers...")
for d in ["communication", "communication/migrations", "templates/communication"]:
    (BASE / d).mkdir(parents=True, exist_ok=True)
print("      OK\n")

print("[2/3] Generation fichiers...")
FILES = {}

# ============================================
# APP COMMUNICATION
# ============================================
FILES["communication/__init__.py"] = ""
FILES["communication/migrations/__init__.py"] = ""

FILES["communication/apps.py"] = '''from django.apps import AppConfig
class CommunicationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'communication'
'''

FILES["communication/models.py"] = '''from django.db import models
from accounts.models import User, Entreprise


class Conversation(models.Model):
    """Conversation entre une entreprise et le support"""
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='conversations')
    sujet = models.CharField(max_length=200)
    fermee = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'conversations'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.entreprise.nom} - {self.sujet}"

    @property
    def nb_messages_non_lus_entreprise(self):
        return self.messages.filter(lu_par_entreprise=False, expediteur__role='SUPER_ADMIN').count()

    @property
    def nb_messages_non_lus_admin(self):
        return self.messages.filter(lu_par_admin=False, expediteur__role='ENTREPRISE').count()


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    expediteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_envoyes')
    contenu = models.TextField()
    piece_jointe = models.FileField(upload_to='messages/%Y/%m/', blank=True, null=True)
    lu_par_entreprise = models.BooleanField(default=False)
    lu_par_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messages'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.expediteur} - {self.created_at}"


class Ticket(models.Model):
    CATEGORIES = [
        ('TECHNIQUE', 'Probleme technique'),
        ('COMPTABILITE', 'Question comptable'),
        ('FACTURATION', 'Facturation / Abonnement'),
        ('FONCTIONNALITE', 'Demande de fonctionnalite'),
        ('AUTRE', 'Autre'),
    ]
    PRIORITES = [
        ('BASSE', 'Basse'),
        ('NORMALE', 'Normale'),
        ('HAUTE', 'Haute'),
        ('URGENTE', 'Urgente'),
    ]
    STATUTS = [
        ('OUVERT', 'Ouvert'),
        ('EN_COURS', 'En cours'),
        ('RESOLU', 'Resolu'),
        ('FERME', 'Ferme'),
    ]

    numero = models.CharField(max_length=20, unique=True, blank=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='tickets')
    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tickets_crees')
    sujet = models.CharField(max_length=200)
    description = models.TextField()
    categorie = models.CharField(max_length=20, choices=CATEGORIES, default='AUTRE')
    priorite = models.CharField(max_length=20, choices=PRIORITES, default='NORMALE')
    statut = models.CharField(max_length=20, choices=STATUTS, default='OUVERT')
    assigne_a = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_assignes')
    piece_jointe = models.FileField(upload_to='tickets/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolu_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tickets'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.numero:
            from django.utils import timezone
            year = timezone.now().year
            last = Ticket.objects.filter(numero__startswith=f'TK-{year}').count() + 1
            self.numero = f'TK-{year}-{last:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero} - {self.sujet}"


class ReponseTicket(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='reponses')
    auteur = models.ForeignKey(User, on_delete=models.CASCADE)
    contenu = models.TextField()
    piece_jointe = models.FileField(upload_to='tickets/reponses/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reponses_tickets'
        ordering = ['created_at']


class Annonce(models.Model):
    TYPES = [
        ('INFO', 'Information'),
        ('MAINTENANCE', 'Maintenance prevue'),
        ('NOUVEAUTE', 'Nouvelle fonctionnalite'),
        ('IMPORTANT', 'Important'),
    ]

    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    type_annonce = models.CharField(max_length=20, choices=TYPES, default='INFO')
    auteur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cible_toutes = models.BooleanField(default=True, help_text="Diffuser a toutes les entreprises")
    entreprises_ciblees = models.ManyToManyField(Entreprise, blank=True, related_name='annonces_ciblees')
    active = models.BooleanField(default=True)
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'annonces'
        ordering = ['-created_at']

    def __str__(self):
        return self.titre


class AnnonceLue(models.Model):
    """Trace des annonces lues par chaque utilisateur"""
    annonce = models.ForeignKey(Annonce, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lu_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'annonces_lues'
        unique_together = ('annonce', 'user')


class DemandeRappel(models.Model):
    STATUTS = [
        ('EN_ATTENTE', 'En attente'),
        ('PROGRAMME', 'Programme'),
        ('EFFECTUE', 'Effectue'),
        ('ANNULE', 'Annule'),
    ]
    CRENEAUX = [
        ('MATIN', 'Matin (8h-12h)'),
        ('APRES_MIDI', 'Apres-midi (14h-17h)'),
        ('SOIR', 'Soir (17h-19h)'),
    ]

    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='rappels')
    demandeur = models.ForeignKey(User, on_delete=models.CASCADE)
    sujet = models.CharField(max_length=200)
    telephone = models.CharField(max_length=20)
    date_souhaitee = models.DateField()
    creneau = models.CharField(max_length=20, choices=CRENEAUX, default='MATIN')
    statut = models.CharField(max_length=20, choices=STATUTS, default='EN_ATTENTE')
    notes_admin = models.TextField(blank=True)
    effectue_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rappels_effectues')
    created_at = models.DateTimeField(auto_now_add=True)
    effectue_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'demandes_rappel'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.entreprise.nom} - {self.sujet}"


class Notification(models.Model):
    TYPES = [
        ('MESSAGE', 'Nouveau message'),
        ('TICKET', 'Ticket'),
        ('ANNONCE', 'Annonce'),
        ('RAPPEL', 'Rappel'),
        ('SYSTEME', 'Systeme'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type_notif = models.CharField(max_length=20, choices=TYPES)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    lien = models.CharField(max_length=300, blank=True, help_text="URL vers la ressource")
    lue = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
'''

FILES["communication/views.py"] = '''from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.utils import timezone
from .models import (Conversation, Message, Ticket, ReponseTicket,
                      Annonce, AnnonceLue, DemandeRappel, Notification)
from accounts.models import Entreprise, User


# ============ MESSAGERIE ============

@login_required
def messagerie(request):
    """Page principale messagerie"""
    if request.user.is_super_admin:
        conversations = Conversation.objects.all().select_related('entreprise')
    elif hasattr(request.user, 'entreprise'):
        conversations = Conversation.objects.filter(entreprise=request.user.entreprise)
    else:
        return redirect('dashboard')
    return render(request, 'communication/messagerie.html', {'conversations': conversations})


@login_required
def conversation_detail(request, pk):
    conv = get_object_or_404(Conversation, pk=pk)

    # Verification acces
    if not request.user.is_super_admin:
        if not hasattr(request.user, 'entreprise') or conv.entreprise != request.user.entreprise:
            return redirect('messagerie')

    # Marquer messages comme lus
    if request.user.is_super_admin:
        conv.messages.filter(lu_par_admin=False).update(lu_par_admin=True)
    else:
        conv.messages.filter(lu_par_entreprise=False).update(lu_par_entreprise=True)

    if request.method == 'POST':
        contenu = request.POST.get('contenu', '').strip()
        if contenu:
            msg = Message.objects.create(
                conversation=conv,
                expediteur=request.user,
                contenu=contenu,
                piece_jointe=request.FILES.get('piece_jointe'),
                lu_par_admin=request.user.is_super_admin,
                lu_par_entreprise=not request.user.is_super_admin,
            )
            conv.updated_at = timezone.now()
            conv.save()

            # Creer notification pour le destinataire
            if request.user.is_super_admin:
                # Notif pour l'entreprise
                Notification.objects.create(
                    user=conv.entreprise.responsable,
                    type_notif='MESSAGE',
                    titre=f'Nouveau message du support',
                    message=contenu[:100],
                    lien=f'/communication/conversation/{conv.id}/',
                )
            else:
                # Notif pour les admins
                for admin in User.objects.filter(role='SUPER_ADMIN'):
                    Notification.objects.create(
                        user=admin,
                        type_notif='MESSAGE',
                        titre=f'Message de {conv.entreprise.nom}',
                        message=contenu[:100],
                        lien=f'/communication/conversation/{conv.id}/',
                    )

            return redirect('conversation_detail', pk=conv.id)

    return render(request, 'communication/conversation_detail.html', {'conv': conv})


@login_required
def nouvelle_conversation(request):
    """Nouvelle conversation depuis une entreprise"""
    if not hasattr(request.user, 'entreprise'):
        return redirect('dashboard')

    if request.method == 'POST':
        sujet = request.POST.get('sujet', '').strip()
        contenu = request.POST.get('contenu', '').strip()
        if sujet and contenu:
            conv = Conversation.objects.create(
                entreprise=request.user.entreprise,
                sujet=sujet,
            )
            Message.objects.create(
                conversation=conv,
                expediteur=request.user,
                contenu=contenu,
                lu_par_entreprise=True,
            )
            # Notifier admins
            for admin in User.objects.filter(role='SUPER_ADMIN'):
                Notification.objects.create(
                    user=admin,
                    type_notif='MESSAGE',
                    titre=f'Nouvelle conversation de {request.user.entreprise.nom}',
                    message=f'{sujet} - {contenu[:80]}',
                    lien=f'/communication/conversation/{conv.id}/',
                )
            messages.success(request, "Conversation creee !")
            return redirect('conversation_detail', pk=conv.id)
    return render(request, 'communication/nouvelle_conversation.html')


# ============ TICKETS ============

@login_required
def tickets_list(request):
    if request.user.is_super_admin:
        tickets = Ticket.objects.all().select_related('entreprise')
    elif hasattr(request.user, 'entreprise'):
        tickets = Ticket.objects.filter(entreprise=request.user.entreprise)
    else:
        return redirect('dashboard')
    return render(request, 'communication/tickets_list.html', {'tickets': tickets})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.is_super_admin:
        if not hasattr(request.user, 'entreprise') or ticket.entreprise != request.user.entreprise:
            return redirect('tickets_list')

    if request.method == 'POST':
        contenu = request.POST.get('contenu', '').strip()
        if contenu:
            ReponseTicket.objects.create(
                ticket=ticket, auteur=request.user, contenu=contenu,
                piece_jointe=request.FILES.get('piece_jointe'),
            )
            if request.user.is_super_admin and ticket.statut == 'OUVERT':
                ticket.statut = 'EN_COURS'
                ticket.save()

            # Notif
            destinataire = ticket.entreprise.responsable if request.user.is_super_admin else None
            if destinataire:
                Notification.objects.create(
                    user=destinataire, type_notif='TICKET',
                    titre=f'Reponse au ticket {ticket.numero}',
                    message=contenu[:100],
                    lien=f'/communication/ticket/{ticket.id}/',
                )
            else:
                for admin in User.objects.filter(role='SUPER_ADMIN'):
                    Notification.objects.create(
                        user=admin, type_notif='TICKET',
                        titre=f'Reponse ticket {ticket.numero}',
                        message=f'{ticket.entreprise.nom}: {contenu[:80]}',
                        lien=f'/communication/ticket/{ticket.id}/',
                    )
            return redirect('ticket_detail', pk=ticket.id)

    return render(request, 'communication/ticket_detail.html', {'ticket': ticket})


@login_required
def nouveau_ticket(request):
    if not hasattr(request.user, 'entreprise'):
        return redirect('dashboard')

    if request.method == 'POST':
        ticket = Ticket.objects.create(
            entreprise=request.user.entreprise,
            cree_par=request.user,
            sujet=request.POST.get('sujet'),
            description=request.POST.get('description'),
            categorie=request.POST.get('categorie', 'AUTRE'),
            priorite=request.POST.get('priorite', 'NORMALE'),
            piece_jointe=request.FILES.get('piece_jointe'),
        )
        for admin in User.objects.filter(role='SUPER_ADMIN'):
            Notification.objects.create(
                user=admin, type_notif='TICKET',
                titre=f'Nouveau ticket {ticket.numero}',
                message=f'{ticket.entreprise.nom} - {ticket.sujet}',
                lien=f'/communication/ticket/{ticket.id}/',
            )
        messages.success(request, f"Ticket {ticket.numero} cree avec succes !")
        return redirect('ticket_detail', pk=ticket.id)

    return render(request, 'communication/nouveau_ticket.html')


@login_required
def changer_statut_ticket(request, pk):
    if not request.user.is_super_admin:
        return JsonResponse({'error': 'Non autorise'}, status=403)
    ticket = get_object_or_404(Ticket, pk=pk)
    nouveau = request.POST.get('statut')
    if nouveau in dict(Ticket.STATUTS):
        ticket.statut = nouveau
        if nouveau == 'RESOLU':
            ticket.resolu_at = timezone.now()
        ticket.save()
        # Notif entreprise
        Notification.objects.create(
            user=ticket.entreprise.responsable, type_notif='TICKET',
            titre=f'Ticket {ticket.numero} - {ticket.get_statut_display()}',
            message=f'Le ticket "{ticket.sujet}" est maintenant : {ticket.get_statut_display()}',
            lien=f'/communication/ticket/{ticket.id}/',
        )
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Statut invalide'}, status=400)


# ============ ANNONCES ============

@login_required
def annonces_list(request):
    if request.user.is_super_admin:
        annonces = Annonce.objects.all()
    elif hasattr(request.user, 'entreprise'):
        annonces = Annonce.objects.filter(
            Q(active=True) & (Q(cible_toutes=True) | Q(entreprises_ciblees=request.user.entreprise))
        ).distinct()
    else:
        annonces = []
    return render(request, 'communication/annonces_list.html', {'annonces': annonces})


@login_required
def nouvelle_annonce(request):
    if not request.user.is_super_admin:
        return redirect('annonces_list')

    if request.method == 'POST':
        annonce = Annonce.objects.create(
            titre=request.POST.get('titre'),
            contenu=request.POST.get('contenu'),
            type_annonce=request.POST.get('type_annonce', 'INFO'),
            auteur=request.user,
            cible_toutes=request.POST.get('cible_toutes') == 'on',
            date_debut=request.POST.get('date_debut') or None,
            date_fin=request.POST.get('date_fin') or None,
        )
        # Notifs pour toutes les entreprises (ou ciblees)
        if annonce.cible_toutes:
            for ent in Entreprise.objects.all():
                Notification.objects.create(
                    user=ent.responsable, type_notif='ANNONCE',
                    titre=f'Nouvelle annonce : {annonce.titre}',
                    message=annonce.contenu[:150],
                    lien='/communication/annonces/',
                )
        messages.success(request, "Annonce publiee !")
        return redirect('annonces_list')
    return render(request, 'communication/nouvelle_annonce.html')


# ============ DEMANDES DE RAPPEL ============

@login_required
def rappels_list(request):
    if request.user.is_super_admin:
        rappels = DemandeRappel.objects.all().select_related('entreprise')
    elif hasattr(request.user, 'entreprise'):
        rappels = DemandeRappel.objects.filter(entreprise=request.user.entreprise)
    else:
        return redirect('dashboard')
    return render(request, 'communication/rappels_list.html', {'rappels': rappels})


@login_required
def demander_rappel(request):
    if not hasattr(request.user, 'entreprise'):
        return redirect('dashboard')

    if request.method == 'POST':
        rappel = DemandeRappel.objects.create(
            entreprise=request.user.entreprise,
            demandeur=request.user,
            sujet=request.POST.get('sujet'),
            telephone=request.POST.get('telephone'),
            date_souhaitee=request.POST.get('date_souhaitee'),
            creneau=request.POST.get('creneau', 'MATIN'),
        )
        for admin in User.objects.filter(role='SUPER_ADMIN'):
            Notification.objects.create(
                user=admin, type_notif='RAPPEL',
                titre=f'Demande de rappel - {request.user.entreprise.nom}',
                message=f'{rappel.sujet} - {rappel.date_souhaitee} ({rappel.get_creneau_display()})',
                lien=f'/communication/rappels/',
            )
        messages.success(request, "Demande de rappel envoyee ! Vous serez contacte rapidement.")
        return redirect('rappels_list')
    return render(request, 'communication/demander_rappel.html')


@login_required
def marquer_rappel_effectue(request, pk):
    if not request.user.is_super_admin:
        return JsonResponse({'error': 'Non autorise'}, status=403)
    r = get_object_or_404(DemandeRappel, pk=pk)
    r.statut = 'EFFECTUE'
    r.effectue_par = request.user
    r.effectue_at = timezone.now()
    r.notes_admin = request.POST.get('notes', '')
    r.save()
    return JsonResponse({'status': 'ok'})


# ============ NOTIFICATIONS ============

@login_required
def notifications_list(request):
    notifs = Notification.objects.filter(user=request.user)
    return render(request, 'communication/notifications.html', {'notifs': notifs})


@login_required
def marquer_notif_lue(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    n.lue = True
    n.save()
    if n.lien:
        return redirect(n.lien)
    return redirect('notifications_list')


@login_required
def marquer_toutes_lues(request):
    Notification.objects.filter(user=request.user, lue=False).update(lue=True)
    return redirect('notifications_list')


def notifications_count(request):
    """API : nombre de notifs non lues"""
    if request.user.is_authenticated:
        count = Notification.objects.filter(user=request.user, lue=False).count()
        return JsonResponse({'count': count})
    return JsonResponse({'count': 0})
'''

FILES["communication/urls.py"] = '''from django.urls import path
from . import views

urlpatterns = [
    # Messagerie
    path('messagerie/', views.messagerie, name='messagerie'),
    path('conversation/<int:pk>/', views.conversation_detail, name='conversation_detail'),
    path('conversation/nouvelle/', views.nouvelle_conversation, name='nouvelle_conversation'),

    # Tickets
    path('tickets/', views.tickets_list, name='tickets_list'),
    path('ticket/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('ticket/nouveau/', views.nouveau_ticket, name='nouveau_ticket'),
    path('ticket/<int:pk>/statut/', views.changer_statut_ticket, name='changer_statut_ticket'),

    # Annonces
    path('annonces/', views.annonces_list, name='annonces_list'),
    path('annonces/nouvelle/', views.nouvelle_annonce, name='nouvelle_annonce'),

    # Rappels
    path('rappels/', views.rappels_list, name='rappels_list'),
    path('rappels/demander/', views.demander_rappel, name='demander_rappel'),
    path('rappels/<int:pk>/effectue/', views.marquer_rappel_effectue, name='marquer_rappel_effectue'),

    # Notifications
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:pk>/lue/', views.marquer_notif_lue, name='marquer_notif_lue'),
    path('notifications/toutes-lues/', views.marquer_toutes_lues, name='marquer_toutes_lues'),
    path('api/notifications-count/', views.notifications_count, name='notifications_count'),
]
'''

FILES["communication/admin.py"] = '''from django.contrib import admin
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
'''

# ============================================
# TEMPLATES
# ============================================

FILES["templates/communication/messagerie.html"] = '''{% extends 'base.html' %}{% block page_title %}Messagerie{% endblock %}{% block page_subtitle %}Communication directe avec ComptaAuto{% endblock %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">
{% if messages %}{% for m in messages %}<div class="alert alert-{{ m.tags }} alert-dismissible fade show">{{ m }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>{% endfor %}{% endif %}

<div class="d-flex justify-content-between mb-4">
<h3 style="font-family:'Playfair Display',serif;">Mes conversations</h3>
{% if not user.is_super_admin %}<a href="{% url 'nouvelle_conversation' %}" class="btn btn-connect"><i class="bi bi-plus-circle"></i> Nouvelle conversation</a>{% endif %}
</div>

<div class="card"><div class="card-body">
{% for conv in conversations %}
<a href="{% url 'conversation_detail' conv.pk %}" class="text-decoration-none">
<div class="facture-card">
<i class="bi bi-chat-dots" style="font-size:1.8rem;"></i>
<div class="flex-grow-1">
<strong>{{ conv.sujet }}</strong>
{% if user.is_super_admin %}<span class="badge bg-light text-dark ms-2">{{ conv.entreprise.nom }}</span>{% endif %}
<br><small class="text-muted">{{ conv.messages.last.contenu|truncatewords:15 }}</small>
</div>
<div class="text-end">
<small class="text-muted">{{ conv.updated_at|timesince }}</small><br>
{% if user.is_super_admin %}
{% if conv.nb_messages_non_lus_admin > 0 %}<span class="badge bg-danger">{{ conv.nb_messages_non_lus_admin }}</span>{% endif %}
{% else %}
{% if conv.nb_messages_non_lus_entreprise > 0 %}<span class="badge bg-danger">{{ conv.nb_messages_non_lus_entreprise }}</span>{% endif %}
{% endif %}
</div>
</div></a>
{% empty %}
<p class="text-muted text-center py-4">Aucune conversation. <a href="{% url 'nouvelle_conversation' %}">Demarrer une discussion</a></p>
{% endfor %}
</div></div>

</div></main></div>
{% endblock %}
'''

FILES["templates/communication/conversation_detail.html"] = '''{% extends 'base.html' %}{% block page_title %}{{ conv.sujet }}{% endblock %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">
<a href="{% url 'messagerie' %}" class="btn btn-link"><i class="bi bi-arrow-left"></i> Retour aux conversations</a>

<div class="card mt-3"><div class="card-body">
<h4>{{ conv.sujet }}</h4>
<p class="text-muted">{{ conv.entreprise.nom }} - Demarree {{ conv.created_at|date:"d/m/Y H:i" }}</p>

<div style="max-height:500px;overflow-y:auto;background:#f8f9fa;padding:20px;border-radius:8px;">
{% for msg in conv.messages.all %}
<div class="d-flex {% if msg.expediteur == user %}justify-content-end{% endif %} mb-3">
<div style="max-width:70%;">
<div class="p-3 rounded" style="background:{% if msg.expediteur == user %}#14706b;color:white;{% else %}white;border:1px solid #eee;{% endif %}">
{{ msg.contenu|linebreaks }}
{% if msg.piece_jointe %}<a href="{{ msg.piece_jointe.url }}" target="_blank" class="d-block mt-2 {% if msg.expediteur == user %}text-white{% endif %}"><i class="bi bi-paperclip"></i> Piece jointe</a>{% endif %}
</div>
<small class="text-muted">{{ msg.expediteur.get_full_name|default:msg.expediteur.email }} - {{ msg.created_at|date:"d/m H:i" }}</small>
</div>
</div>
{% endfor %}
</div>

<form method="POST" enctype="multipart/form-data" class="mt-4">{% csrf_token %}
<div class="mb-3"><textarea name="contenu" class="form-control" rows="3" placeholder="Tapez votre message..." required></textarea></div>
<div class="d-flex gap-2">
<input type="file" name="piece_jointe" class="form-control" style="max-width:300px;">
<button type="submit" class="btn btn-connect"><i class="bi bi-send"></i> Envoyer</button>
</div>
</form>
</div></div>

</div></main></div>
{% endblock %}
'''

FILES["templates/communication/nouvelle_conversation.html"] = '''{% extends 'base.html' %}{% block page_title %}Nouvelle conversation{% endblock %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">
<a href="{% url 'messagerie' %}" class="btn btn-link"><i class="bi bi-arrow-left"></i> Retour</a>
<div class="card mt-3"><div class="card-body">
<h4>Demarrer une conversation avec le support</h4>
<form method="POST">{% csrf_token %}
<div class="mb-3"><label>Sujet</label><input type="text" name="sujet" class="form-control" placeholder="Ex: Question sur la TVA" required></div>
<div class="mb-3"><label>Votre message</label><textarea name="contenu" class="form-control" rows="6" placeholder="Decrivez votre demande..." required></textarea></div>
<button type="submit" class="btn btn-connect"><i class="bi bi-send"></i> Envoyer</button>
</form>
</div></div>
</div></main></div>
{% endblock %}
'''

FILES["templates/communication/tickets_list.html"] = '''{% extends 'base.html' %}{% block page_title %}Tickets de support{% endblock %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">
<div class="d-flex justify-content-between mb-4">
<h3 style="font-family:'Playfair Display',serif;">Tickets de support</h3>
{% if not user.is_super_admin %}<a href="{% url 'nouveau_ticket' %}" class="btn btn-connect"><i class="bi bi-plus-circle"></i> Nouveau ticket</a>{% endif %}
</div>

<div class="card"><div class="card-body">
<table class="table">
<thead><tr><th>N° Ticket</th>{% if user.is_super_admin %}<th>Entreprise</th>{% endif %}<th>Sujet</th><th>Categorie</th><th>Priorite</th><th>Statut</th><th>Cree le</th></tr></thead>
<tbody>
{% for t in tickets %}
<tr style="cursor:pointer;" onclick="location.href='{% url 'ticket_detail' t.pk %}'">
<td><strong>{{ t.numero }}</strong></td>
{% if user.is_super_admin %}<td>{{ t.entreprise.nom }}</td>{% endif %}
<td>{{ t.sujet }}</td>
<td><span class="badge bg-secondary">{{ t.get_categorie_display }}</span></td>
<td><span class="badge bg-{% if t.priorite == 'URGENTE' %}danger{% elif t.priorite == 'HAUTE' %}warning{% elif t.priorite == 'NORMALE' %}info{% else %}secondary{% endif %}">{{ t.get_priorite_display }}</span></td>
<td><span class="badge bg-{% if t.statut == 'RESOLU' %}success{% elif t.statut == 'EN_COURS' %}primary{% elif t.statut == 'OUVERT' %}warning{% else %}secondary{% endif %}">{{ t.get_statut_display }}</span></td>
<td>{{ t.created_at|date:"d/m/Y" }}</td>
</tr>
{% empty %}<tr><td colspan="7" class="text-center text-muted">Aucun ticket</td></tr>{% endfor %}
</tbody></table>
</div></div>

</div></main></div>
{% endblock %}
'''

FILES["templates/communication/ticket_detail.html"] = '''{% extends 'base.html' %}{% block page_title %}Ticket {{ ticket.numero }}{% endblock %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">
<a href="{% url 'tickets_list' %}" class="btn btn-link"><i class="bi bi-arrow-left"></i> Retour</a>

<div class="card mt-3"><div class="card-body">
<div class="d-flex justify-content-between align-items-start">
<div>
<h4>{{ ticket.numero }} - {{ ticket.sujet }}</h4>
<p class="text-muted">{{ ticket.entreprise.nom }} - Cree par {{ ticket.cree_par.get_full_name }} - {{ ticket.created_at|date:"d/m/Y H:i" }}</p>
</div>
<div>
<span class="badge bg-secondary me-1">{{ ticket.get_categorie_display }}</span>
<span class="badge bg-{% if ticket.priorite == 'URGENTE' %}danger{% elif ticket.priorite == 'HAUTE' %}warning{% else %}info{% endif %} me-1">{{ ticket.get_priorite_display }}</span>
<span class="badge bg-{% if ticket.statut == 'RESOLU' %}success{% elif ticket.statut == 'EN_COURS' %}primary{% elif ticket.statut == 'OUVERT' %}warning{% else %}secondary{% endif %}">{{ ticket.get_statut_display }}</span>
</div>
</div>

{% if user.is_super_admin %}
<div class="mt-3">
<label>Changer le statut :</label>
<div class="btn-group">
<button class="btn btn-sm btn-outline-warning" onclick="changerStatut('OUVERT')">Ouvert</button>
<button class="btn btn-sm btn-outline-primary" onclick="changerStatut('EN_COURS')">En cours</button>
<button class="btn btn-sm btn-outline-success" onclick="changerStatut('RESOLU')">Resolu</button>
<button class="btn btn-sm btn-outline-secondary" onclick="changerStatut('FERME')">Ferme</button>
</div>
</div>
{% endif %}

<hr>
<div class="p-3 bg-light rounded">
<strong>Description initiale :</strong>
<p>{{ ticket.description|linebreaks }}</p>
{% if ticket.piece_jointe %}<a href="{{ ticket.piece_jointe.url }}" target="_blank"><i class="bi bi-paperclip"></i> Piece jointe</a>{% endif %}
</div>

<h5 class="mt-4">Conversations ({{ ticket.reponses.count }})</h5>
<div style="max-height:400px;overflow-y:auto;">
{% for r in ticket.reponses.all %}
<div class="border-start border-3 ps-3 mb-3 {% if r.auteur.is_super_admin %}border-warning{% else %}border-primary{% endif %}">
<div class="d-flex justify-content-between">
<strong>{{ r.auteur.get_full_name|default:r.auteur.email }} {% if r.auteur.is_super_admin %}<span class="badge bg-warning text-dark">Support</span>{% endif %}</strong>
<small class="text-muted">{{ r.created_at|date:"d/m H:i" }}</small>
</div>
<p>{{ r.contenu|linebreaks }}</p>
{% if r.piece_jointe %}<a href="{{ r.piece_jointe.url }}" target="_blank"><i class="bi bi-paperclip"></i> Piece jointe</a>{% endif %}
</div>
{% endfor %}
</div>

{% if ticket.statut != 'FERME' %}
<form method="POST" enctype="multipart/form-data" class="mt-4">{% csrf_token %}
<div class="mb-3"><textarea name="contenu" class="form-control" rows="4" placeholder="Repondre..." required></textarea></div>
<div class="d-flex gap-2">
<input type="file" name="piece_jointe" class="form-control" style="max-width:300px;">
<button type="submit" class="btn btn-connect"><i class="bi bi-send"></i> Repondre</button>
</div>
</form>
{% endif %}
</div></div>

</div></main></div>
<script>
function getCookie(n){const v=`; ${document.cookie}`.split(`; ${n}=`);if(v.length===2)return v.pop().split(';').shift();}
async function changerStatut(s){
    const fd = new FormData(); fd.append('statut', s);
    const r = await fetch('/communication/ticket/{{ ticket.pk }}/statut/', {method:'POST', headers:{'X-CSRFToken':getCookie('csrftoken')}, body:fd});
    if(r.ok) location.reload();
}
</script>
{% endblock %}
'''

FILES["templates/communication/nouveau_ticket.html"] = '''{% extends 'base.html' %}{% block page_title %}Nouveau ticket{% endblock %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">
<a href="{% url 'tickets_list' %}" class="btn btn-link"><i class="bi bi-arrow-left"></i> Retour</a>
<div class="card mt-3"><div class="card-body">
<h4>Ouvrir un ticket de support</h4>
<form method="POST" enctype="multipart/form-data">{% csrf_token %}
<div class="row">
<div class="col-md-6 mb-3"><label>Categorie</label><select name="categorie" class="form-select" required>
<option value="TECHNIQUE">Probleme technique</option>
<option value="COMPTABILITE">Question comptable</option>
<option value="FACTURATION">Facturation / Abonnement</option>
<option value="FONCTIONNALITE">Demande de fonctionnalite</option>
<option value="AUTRE">Autre</option>
</select></div>
<div class="col-md-6 mb-3"><label>Priorite</label><select name="priorite" class="form-select" required>
<option value="BASSE">Basse</option>
<option value="NORMALE" selected>Normale</option>
<option value="HAUTE">Haute</option>
<option value="URGENTE">Urgente</option>
</select></div>
<div class="col-12 mb-3"><label>Sujet</label><input type="text" name="sujet" class="form-control" required></div>
<div class="col-12 mb-3"><label>Description detaillee</label><textarea name="description" class="form-control" rows="6" required></textarea></div>
<div class="col-12 mb-3"><label>Piece jointe (optionnel)</label><input type="file" name="piece_jointe" class="form-control"></div>
</div>
<button type="submit" class="btn btn-connect"><i class="bi bi-send"></i> Creer le ticket</button>
</form>
</div></div>
</div></main></div>
{% endblock %}
'''

FILES["templates/communication/annonces_list.html"] = '''{% extends 'base.html' %}{% block page_title %}Annonces{% endblock %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">
<div class="d-flex justify-content-between mb-4">
<h3 style="font-family:'Playfair Display',serif;">Annonces ComptaAuto</h3>
{% if user.is_super_admin %}<a href="{% url 'nouvelle_annonce' %}" class="btn btn-connect"><i class="bi bi-megaphone"></i> Nouvelle annonce</a>{% endif %}
</div>

{% for a in annonces %}
<div class="card mb-3"><div class="card-body">
<div class="d-flex justify-content-between">
<h5>
<span class="badge bg-{% if a.type_annonce == 'IMPORTANT' %}danger{% elif a.type_annonce == 'MAINTENANCE' %}warning{% elif a.type_annonce == 'NOUVEAUTE' %}success{% else %}info{% endif %} me-2">{{ a.get_type_annonce_display }}</span>
{{ a.titre }}
</h5>
<small class="text-muted">{{ a.created_at|date:"d/m/Y H:i" }}</small>
</div>
<p>{{ a.contenu|linebreaks }}</p>
{% if a.date_debut or a.date_fin %}<small class="text-muted">Periode : {{ a.date_debut|default:"-" }} au {{ a.date_fin|default:"-" }}</small>{% endif %}
</div></div>
{% empty %}
<p class="text-muted text-center py-5">Aucune annonce pour le moment.</p>
{% endfor %}

</div></main></div>
{% endblock %}
'''

FILES["templates/communication/nouvelle_annonce.html"] = '''{% extends 'base.html' %}{% block page_title %}Nouvelle annonce{% endblock %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">
<a href="{% url 'annonces_list' %}" class="btn btn-link"><i class="bi bi-arrow-left"></i> Retour</a>
<div class="card mt-3"><div class="card-body">
<h4>Publier une annonce</h4>
<form method="POST">{% csrf_token %}
<div class="row">
<div class="col-md-8 mb-3"><label>Titre</label><input type="text" name="titre" class="form-control" required></div>
<div class="col-md-4 mb-3"><label>Type</label><select name="type_annonce" class="form-select">
<option value="INFO">Information</option>
<option value="MAINTENANCE">Maintenance</option>
<option value="NOUVEAUTE">Nouveaute</option>
<option value="IMPORTANT">Important</option>
</select></div>
<div class="col-12 mb-3"><label>Contenu</label><textarea name="contenu" class="form-control" rows="6" required></textarea></div>
<div class="col-md-6 mb-3"><label>Date debut (optionnel)</label><input type="date" name="date_debut" class="form-control"></div>
<div class="col-md-6 mb-3"><label>Date fin (optionnel)</label><input type="date" name="date_fin" class="form-control"></div>
<div class="col-12 mb-3"><label><input type="checkbox" name="cible_toutes" checked> Diffuser a toutes les entreprises</label></div>
</div>
<button type="submit" class="btn btn-connect"><i class="bi bi-megaphone"></i> Publier</button>
</form>
</div></div>
</div></main></div>
{% endblock %}
'''

FILES["templates/communication/rappels_list.html"] = '''{% extends 'base.html' %}{% block page_title %}Demandes de rappel{% endblock %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">
<div class="d-flex justify-content-between mb-4">
<h3 style="font-family:'Playfair Display',serif;">Demandes de rappel telephonique</h3>
{% if not user.is_super_admin %}<a href="{% url 'demander_rappel' %}" class="btn btn-connect"><i class="bi bi-telephone-plus"></i> Demander un rappel</a>{% endif %}
</div>

<div class="card"><div class="card-body">
<table class="table">
<thead><tr>{% if user.is_super_admin %}<th>Entreprise</th>{% endif %}<th>Sujet</th><th>Telephone</th><th>Date souhaitee</th><th>Creneau</th><th>Statut</th>{% if user.is_super_admin %}<th>Action</th>{% endif %}</tr></thead>
<tbody>
{% for r in rappels %}
<tr>
{% if user.is_super_admin %}<td>{{ r.entreprise.nom }}</td>{% endif %}
<td>{{ r.sujet }}</td>
<td><strong>{{ r.telephone }}</strong></td>
<td>{{ r.date_souhaitee|date:"d/m/Y" }}</td>
<td>{{ r.get_creneau_display }}</td>
<td><span class="badge bg-{% if r.statut == 'EFFECTUE' %}success{% elif r.statut == 'PROGRAMME' %}primary{% elif r.statut == 'EN_ATTENTE' %}warning{% else %}secondary{% endif %}">{{ r.get_statut_display }}</span></td>
{% if user.is_super_admin and r.statut == 'EN_ATTENTE' %}<td><button class="btn btn-sm btn-success" onclick="effectue({{ r.pk }})">Marquer effectue</button></td>{% else %}{% if user.is_super_admin %}<td>-</td>{% endif %}{% endif %}
</tr>
{% empty %}<tr><td colspan="{% if user.is_super_admin %}7{% else %}5{% endif %}" class="text-center text-muted">Aucun rappel</td></tr>{% endfor %}
</tbody></table>
</div></div>

</div></main></div>
<script>
function getCookie(n){const v=`; ${document.cookie}`.split(`; ${n}=`);if(v.length===2)return v.pop().split(';').shift();}
async function effectue(id){
    const notes = prompt('Notes (optionnel) :');
    const fd = new FormData(); if(notes) fd.append('notes', notes);
    const r = await fetch('/communication/rappels/'+id+'/effectue/', {method:'POST', headers:{'X-CSRFToken':getCookie('csrftoken')}, body:fd});
    if(r.ok) location.reload();
}
</script>
{% endblock %}
'''

FILES["templates/communication/demander_rappel.html"] = '''{% extends 'base.html' %}{% block page_title %}Demander un rappel{% endblock %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">
<a href="{% url 'rappels_list' %}" class="btn btn-link"><i class="bi bi-arrow-left"></i> Retour</a>
<div class="card mt-3"><div class="card-body">
<h4>Demander un rappel telephonique</h4>
<p class="text-muted">Notre equipe vous contactera au creneau choisi.</p>
<form method="POST">{% csrf_token %}
<div class="row">
<div class="col-12 mb-3"><label>Sujet du rappel</label><input type="text" name="sujet" class="form-control" placeholder="Ex: Aide pour configuration TVA" required></div>
<div class="col-md-6 mb-3"><label>Numero de telephone</label><input type="tel" name="telephone" class="form-control" value="{{ user.telephone }}" required></div>
<div class="col-md-6 mb-3"><label>Date souhaitee</label><input type="date" name="date_souhaitee" class="form-control" required></div>
<div class="col-12 mb-3"><label>Creneau prefere</label><select name="creneau" class="form-select">
<option value="MATIN">Matin (8h-12h)</option>
<option value="APRES_MIDI">Apres-midi (14h-17h)</option>
<option value="SOIR">Soir (17h-19h)</option>
</select></div>
</div>
<button type="submit" class="btn btn-connect"><i class="bi bi-telephone-plus"></i> Confirmer la demande</button>
</form>
</div></div>
</div></main></div>
{% endblock %}
'''

FILES["templates/communication/notifications.html"] = '''{% extends 'base.html' %}{% block page_title %}Notifications{% endblock %}{% block content %}
<div class="app-layout">{% include 'partials/sidebar.html' %}<main class="main-content">{% include 'partials/topbar.html' %}
<div class="content-area">
<div class="d-flex justify-content-between mb-4">
<h3 style="font-family:'Playfair Display',serif;">Notifications</h3>
<a href="{% url 'marquer_toutes_lues' %}" class="btn btn-outline-secondary"><i class="bi bi-check-all"></i> Tout marquer comme lu</a>
</div>

<div class="card"><div class="card-body">
{% for n in notifs %}
<a href="{% url 'marquer_notif_lue' n.pk %}" class="text-decoration-none">
<div class="border-bottom py-3 d-flex align-items-center {% if not n.lue %}bg-light{% endif %}" style="padding:15px;border-radius:8px;">
<div class="me-3"><i class="bi bi-{% if n.type_notif == 'MESSAGE' %}chat-dots{% elif n.type_notif == 'TICKET' %}ticket-perforated{% elif n.type_notif == 'ANNONCE' %}megaphone{% elif n.type_notif == 'RAPPEL' %}telephone{% else %}info-circle{% endif %}" style="font-size:2rem;color:#14706b;"></i></div>
<div class="flex-grow-1">
<strong style="color:#1a3e3a;">{{ n.titre }}</strong>
{% if not n.lue %}<span class="badge bg-danger ms-2">Nouveau</span>{% endif %}
<br><small class="text-muted">{{ n.message }}</small>
</div>
<small class="text-muted">{{ n.created_at|timesince }}</small>
</div></a>
{% empty %}<p class="text-muted text-center py-5">Aucune notification</p>{% endfor %}
</div></div>

</div></main></div>
{% endblock %}
'''

# ============================================
# MISE A JOUR DE SIDEBAR + TOPBAR pour les notifs
# ============================================
FILES["templates/partials/sidebar.html"] = '''<aside class="sidebar">
<div class="sidebar-brand"><div class="logo-icon">C</div><div><h1 class="brand-title">ComptaAuto</h1><p class="brand-subtitle">COMPTABILITE</p></div></div>
<div class="sidebar-section">PILOTAGE</div>
<nav class="sidebar-nav"><a href="{% url 'dashboard' %}" class="nav-item {% if request.resolver_match.url_name == 'dashboard' %}active{% endif %}"><i class="bi bi-grid-1x2"></i> Tableau de bord</a></nav>

<div class="sidebar-section">OPERATIONS</div>
<nav class="sidebar-nav">
<a href="{% url 'ocr_page' %}" class="nav-item {% if 'ocr' in request.path %}active{% endif %}"><i class="bi bi-text-paragraph"></i> Saisie OCR</a>
<a href="{% url 'rapprochement_page' %}" class="nav-item {% if 'rapprochement' in request.path %}active{% endif %}"><i class="bi bi-arrow-left-right"></i> Rapprochement</a>
<a href="{% url 'ecritures' %}" class="nav-item {% if 'ecriture' in request.path %}active{% endif %}"><i class="bi bi-journal-text"></i> Ecritures</a>
<a href="{% url 'nouvelle_ecriture' %}" class="nav-item"><i class="bi bi-plus-circle"></i> Nouvelle ecriture</a>
</nav>

<div class="sidebar-section">REPORTING & ALERTES</div>
<nav class="sidebar-nav">
<a href="{% url 'reporting_index' %}" class="nav-item {% if 'reporting' in request.path %}active{% endif %}"><i class="bi bi-bar-chart-line"></i> Reporting financier</a>
<a href="{% url 'alertes_page' %}" class="nav-item {% if 'alerte' in request.path %}active{% endif %}"><i class="bi bi-bell"></i> Alertes</a>
</nav>

<div class="sidebar-section">SUPPORT</div>
<nav class="sidebar-nav">
<a href="{% url 'messagerie' %}" class="nav-item {% if 'conversation' in request.path or 'messagerie' in request.path %}active{% endif %}"><i class="bi bi-chat-dots"></i> Messagerie</a>
<a href="{% url 'tickets_list' %}" class="nav-item {% if 'ticket' in request.path %}active{% endif %}"><i class="bi bi-ticket-perforated"></i> Tickets support</a>
<a href="{% url 'annonces_list' %}" class="nav-item {% if 'annonce' in request.path %}active{% endif %}"><i class="bi bi-megaphone"></i> Annonces</a>
<a href="{% url 'rappels_list' %}" class="nav-item {% if 'rappel' in request.path %}active{% endif %}"><i class="bi bi-telephone"></i> Demandes rappel</a>
</nav>

<div class="sidebar-section">CONFIGURATION</div>
<nav class="sidebar-nav">
<a href="{% url 'init_plan' %}" class="nav-item"><i class="bi bi-list-ol"></i> Initialiser plan</a>
</nav>

<div class="sidebar-footer"><strong>{{ user.entreprise.nom|default:user.get_full_name }}</strong><small>SYSCOHADA - Exercice {{ user.entreprise.exercice_courant|default:'2026' }}</small></div>
</aside>
'''

FILES["templates/partials/topbar.html"] = '''<header class="topbar"><div>
<h2 class="topbar-title">{% block page_title %}Tableau de bord{% endblock %}</h2>
<p class="topbar-subtitle">{% block page_subtitle %}Vue financiere en temps reel{% endblock %}</p></div>
<div class="topbar-actions">
<a href="{% url 'notifications_list' %}" class="position-relative" style="color:#14706b;text-decoration:none;font-size:1.5rem;">
<i class="bi bi-bell-fill"></i>
<span id="notifCount" class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger" style="display:none;">0</span>
</a>
<div class="user-info"><div class="user-avatar">{{ user.first_name.0|default:user.email.0|upper }}</div><div><strong>{{ user.get_full_name|default:user.email }}</strong><small>{{ user.entreprise.nom|default:'' }}</small></div></div>
<a href="{% url 'logout' %}" class="btn btn-outline-danger btn-sm">Deconnexion</a></div></header>
<script>
function updateNotifCount(){
    fetch('/communication/api/notifications-count/').then(r=>r.json()).then(d=>{
        const b = document.getElementById('notifCount');
        if(d.count > 0){ b.textContent = d.count; b.style.display = 'inline-block'; }
        else { b.style.display = 'none'; }
    });
}
updateNotifCount();
setInterval(updateNotifCount, 30000);
</script>
'''

# ============================================
# UPDATE SETTINGS + URLS
# ============================================
FILES["comptaauto/settings.py"] = '''from pathlib import Path
import environ, os

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='dev-key-change-me')
DEBUG = env('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', '*'])

INSTALLED_APPS = [
    'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes',
    'django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles',
    'accounts','comptabilite','ocr_app','dashboard',
    'rapprochement','reporting','alertes','communication',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'comptaauto.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
WSGI_APPLICATION = 'comptaauto.wsgi.application'

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_USER_MODEL = 'accounts.User'
AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Abidjan'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
OCR_SPACE_API_KEY = env('OCR_SPACE_API_KEY', default='helloworld')
'''

FILES["comptaauto/urls.py"] = '''from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', lambda r: redirect('login')),
    path('', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('admin-panel/', include('dashboard.urls_admin')),
    path('comptabilite/', include('comptabilite.urls')),
    path('ocr/', include('ocr_app.urls')),
    path('rapprochement/', include('rapprochement.urls')),
    path('reporting/', include('reporting.urls')),
    path('alertes/', include('alertes.urls')),
    path('communication/', include('communication.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
'''

# Ecriture
for fp, content in FILES.items():
    p = BASE / fp
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"      [OK] {fp}")

print(f"\n      {len(FILES)} fichiers crees/mis a jour\n")

# Migrations
print("[3/3] Migrations base de donnees...")
subprocess.run([PY, "manage.py", "makemigrations", "communication"], check=True)
subprocess.run([PY, "manage.py", "migrate"], check=True)
print("      OK")

print("\n" + "="*65)
print("  SYSTEME DE COMMUNICATION INSTALLE !")
print("="*65)
print(f"\nRelancer le serveur :")
print(f"   {PY} manage.py runserver")
print(f"\nNouvelles fonctionnalites accessibles :")
print(f"  - Messagerie     : /communication/messagerie/")
print(f"  - Tickets        : /communication/tickets/")
print(f"  - Annonces       : /communication/annonces/")
print(f"  - Demande rappel : /communication/rappels/")
print(f"  - Notifications  : /communication/notifications/")
print(f"\nLa cloche de notification est dans la topbar !")
print("="*65 + "\n")