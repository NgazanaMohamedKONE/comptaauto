from django.db import models
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
