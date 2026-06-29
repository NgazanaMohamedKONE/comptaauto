from django.shortcuts import render, redirect, get_object_or_404
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
