from django.db import models
from django.utils import timezone
from datetime import timedelta
from accounts.models import Entreprise, User


class Forfait(models.Model):
    """Forfaits disponibles"""
    CODES = [
        ('FREEMIUM', 'Freemium (Essai)'),
        ('STARTER', 'Starter'),
        ('PRO', 'Pro'),
        ('ENTERPRISE', 'Enterprise'),
        ('ANNUEL', 'Annuel'),
    ]

    code = models.CharField(max_length=20, choices=CODES, unique=True)
    nom = models.CharField(max_length=100)
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    duree_jours = models.IntegerField()
    description = models.TextField(blank=True)

    # Limites
    max_factures_ocr_mois = models.IntegerField(default=10)
    max_utilisateurs = models.IntegerField(default=1)
    max_ecritures_mois = models.IntegerField(default=50)
    rapprochement_bancaire = models.BooleanField(default=False)
    reporting_avance = models.BooleanField(default=False)
    support_prioritaire = models.BooleanField(default=False)
    export_illimite = models.BooleanField(default=False)

    # Affichage
    couleur = models.CharField(max_length=20, default='#14706b')
    icone = models.CharField(max_length=50, default='bi-star')
    populaire = models.BooleanField(default=False)
    actif = models.BooleanField(default=True)
    ordre = models.IntegerField(default=0)

    class Meta:
        db_table = 'forfaits'
        ordering = ['ordre', 'prix']

    def __str__(self):
        return f"{self.nom} ({self.prix} FCFA)"

    @property
    def prix_par_jour(self):
        return self.prix / self.duree_jours if self.duree_jours else 0


class Abonnement(models.Model):
    """Abonnement actif d'une entreprise"""
    STATUTS = [
        ('ACTIF', 'Actif'),
        ('EXPIRE', 'Expire'),
        ('SUSPENDU', 'Suspendu'),
        ('ANNULE', 'Annule'),
    ]

    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='abonnements')
    forfait = models.ForeignKey(Forfait, on_delete=models.PROTECT)
    date_debut = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField()
    statut = models.CharField(max_length=20, choices=STATUTS, default='ACTIF')
    auto_renouvellement = models.BooleanField(default=False)
    renouvelle_de = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    # Compteurs d'usage du mois
    factures_ocr_utilisees = models.IntegerField(default=0)
    ecritures_utilisees = models.IntegerField(default=0)

    class Meta:
        db_table = 'abonnements'
        ordering = ['-date_debut']

    def __str__(self):
        return f"{self.entreprise.nom} - {self.forfait.nom}"

    @property
    def jours_restants(self):
        if self.statut != 'ACTIF':
            return 0
        delta = self.date_fin - timezone.now()
        return max(0, delta.days)

    @property
    def heures_restantes(self):
        if self.statut != 'ACTIF':
            return 0
        delta = self.date_fin - timezone.now()
        return max(0, int(delta.total_seconds() / 3600))

    @property
    def pourcentage_restant(self):
        total = (self.date_fin - self.date_debut).days
        if total == 0: return 0
        return int((self.jours_restants / total) * 100)

    @property
    def est_expire(self):
        return self.date_fin < timezone.now()

    @property
    def pourcentage_ocr(self):
        if not self.forfait.max_factures_ocr_mois: return 0
        return int((self.factures_ocr_utilisees / self.forfait.max_factures_ocr_mois) * 100)

    def verifier_et_expirer(self):
        if self.est_expire and self.statut == 'ACTIF':
            self.statut = 'EXPIRE'
            self.save()
            return True
        return False


class Paiement(models.Model):
    """Historique des paiements"""
    METHODES = [
        ('MOBILE_MONEY', 'Mobile Money (Orange/MTN/Moov)'),
        ('CARTE', 'Carte bancaire'),
        ('VIREMENT', 'Virement bancaire'),
        ('ESPECES', 'Especes'),
        ('CHEQUE', 'Cheque'),
    ]
    STATUTS = [
        ('EN_ATTENTE', 'En attente'),
        ('VALIDE', 'Valide'),
        ('REFUSE', 'Refuse'),
        ('REMBOURSE', 'Rembourse'),
    ]

    reference = models.CharField(max_length=50, unique=True, blank=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='paiements')
    abonnement = models.ForeignKey(Abonnement, on_delete=models.SET_NULL, null=True, blank=True)
    forfait = models.ForeignKey(Forfait, on_delete=models.PROTECT)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    methode = models.CharField(max_length=20, choices=METHODES, default='MOBILE_MONEY')
    statut = models.CharField(max_length=20, choices=STATUTS, default='EN_ATTENTE')
    numero_transaction = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    paye_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    valide_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements_valides')
    created_at = models.DateTimeField(auto_now_add=True)
    valide_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'paiements'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.reference:
            year = timezone.now().year
            last = Paiement.objects.filter(reference__startswith=f'PAY-{year}').count() + 1
            self.reference = f'PAY-{year}-{last:05d}'
        super().save(*args, **kwargs)


def init_forfaits():
    """Initialise les 5 forfaits par defaut"""
    forfaits_data = [
        {
            'code': 'FREEMIUM', 'nom': 'Freemium (Essai 7 jours)', 'prix': 0, 'duree_jours': 7,
            'description': 'Essai gratuit pour decouvrir ComptaAuto',
            'max_factures_ocr_mois': 5, 'max_utilisateurs': 1, 'max_ecritures_mois': 20,
            'rapprochement_bancaire': False, 'reporting_avance': False,
            'couleur': '#6b8884', 'icone': 'bi-gift', 'ordre': 1,
        },
        {
            'code': 'STARTER', 'nom': 'Starter', 'prix': 25000, 'duree_jours': 30,
            'description': 'Pour les petites entreprises et auto-entrepreneurs',
            'max_factures_ocr_mois': 50, 'max_utilisateurs': 2, 'max_ecritures_mois': 200,
            'rapprochement_bancaire': True, 'reporting_avance': False,
            'couleur': '#14706b', 'icone': 'bi-rocket', 'ordre': 2,
        },
        {
            'code': 'PRO', 'nom': 'Pro', 'prix': 60000, 'duree_jours': 30,
            'description': 'Pour les PME en croissance',
            'max_factures_ocr_mois': 200, 'max_utilisateurs': 5, 'max_ecritures_mois': 1000,
            'rapprochement_bancaire': True, 'reporting_avance': True,
            'support_prioritaire': True,
            'couleur': '#1a8b85', 'icone': 'bi-stars', 'ordre': 3, 'populaire': True,
        },
        {
            'code': 'ENTERPRISE', 'nom': 'Enterprise', 'prix': 120000, 'duree_jours': 30,
            'description': 'Pour les grandes structures multi-sites',
            'max_factures_ocr_mois': 1000, 'max_utilisateurs': 20, 'max_ecritures_mois': 10000,
            'rapprochement_bancaire': True, 'reporting_avance': True,
            'support_prioritaire': True, 'export_illimite': True,
            'couleur': '#9b59b6', 'icone': 'bi-building', 'ordre': 4,
        },
        {
            'code': 'ANNUEL', 'nom': 'Annuel (12 mois)', 'prix': 300000, 'duree_jours': 365,
            'description': 'Pro pendant 12 mois - Economisez 50% !',
            'max_factures_ocr_mois': 200, 'max_utilisateurs': 5, 'max_ecritures_mois': 1000,
            'rapprochement_bancaire': True, 'reporting_avance': True,
            'support_prioritaire': True, 'export_illimite': True,
            'couleur': '#f4b860', 'icone': 'bi-trophy', 'ordre': 5,
        },
    ]

    for data in forfaits_data:
        Forfait.objects.update_or_create(code=data['code'], defaults=data)
