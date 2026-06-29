"""
Modeles supplementaires Pack 2
"""
from django.db import models
from django.utils import timezone
from accounts.models import User, Entreprise


class ParametreSysteme(models.Model):
    """Parametres globaux de la plateforme"""
    cle = models.CharField(max_length=100, unique=True)
    valeur = models.TextField()
    description = models.TextField(blank=True)
    type_valeur = models.CharField(max_length=20, default='TEXT',
        choices=[('TEXT', 'Texte'), ('NUMBER', 'Nombre'), ('BOOLEAN', 'Booleen'), ('JSON', 'JSON')])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'parametres_systeme'

    def __str__(self):
        return self.cle


class CouponPromo(models.Model):
    """Codes promo / coupons"""
    TYPES_REDUCTION = [
        ('POURCENTAGE', 'Pourcentage'),
        ('MONTANT', 'Montant fixe'),
        ('JOURS_GRATUITS', 'Jours gratuits'),
    ]

    code = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=200)
    type_reduction = models.CharField(max_length=20, choices=TYPES_REDUCTION, default='POURCENTAGE')
    valeur = models.DecimalField(max_digits=10, decimal_places=2)
    date_debut = models.DateField()
    date_fin = models.DateField()
    max_utilisations = models.IntegerField(default=100)
    nb_utilisations = models.IntegerField(default=0)
    actif = models.BooleanField(default=True)
    forfaits_eligibles = models.ManyToManyField('abonnements.Forfait', blank=True,
        help_text="Vide = tous les forfaits")
    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coupons_promo'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.valeur}{'%' if self.type_reduction == 'POURCENTAGE' else 'F'}"

    @property
    def est_valide(self):
        today = timezone.now().date()
        return (self.actif and
                self.date_debut <= today <= self.date_fin and
                self.nb_utilisations < self.max_utilisations)


class UtilisationCoupon(models.Model):
    """Historique d'utilisation des coupons"""
    coupon = models.ForeignKey(CouponPromo, on_delete=models.CASCADE, related_name='utilisations')
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE)
    paiement = models.ForeignKey('abonnements.Paiement', on_delete=models.CASCADE, null=True)
    reduction_appliquee = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'utilisations_coupons'


class CampagneEmail(models.Model):
    """Campagnes email aux entreprises"""
    STATUTS = [
        ('BROUILLON', 'Brouillon'),
        ('PROGRAMMEE', 'Programmee'),
        ('ENVOYEE', 'Envoyee'),
        ('ANNULEE', 'Annulee'),
    ]

    nom = models.CharField(max_length=200)
    sujet = models.CharField(max_length=200)
    contenu = models.TextField()

    # Ciblage
    cible_toutes = models.BooleanField(default=True)
    cible_actives = models.BooleanField(default=True, help_text="Uniquement entreprises avec abonnement actif")
    cible_forfaits = models.ManyToManyField('abonnements.Forfait', blank=True)
    entreprises_destinataires = models.ManyToManyField(Entreprise, blank=True, related_name='campagnes_recues')

    statut = models.CharField(max_length=20, choices=STATUTS, default='BROUILLON')
    nb_destinataires = models.IntegerField(default=0)
    nb_envoyes = models.IntegerField(default=0)
    date_envoi_prevue = models.DateTimeField(null=True, blank=True)
    date_envoi_effective = models.DateTimeField(null=True, blank=True)

    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'campagnes_email'
        ordering = ['-created_at']

    def __str__(self):
        return self.nom


class RapportMensuel(models.Model):
    """Rapports mensuels generes"""
    mois = models.IntegerField()
    annee = models.IntegerField()
    fichier_pdf = models.FileField(upload_to='rapports/%Y/', null=True, blank=True)

    # Donnees du rapport
    revenus_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    nb_nouveaux_clients = models.IntegerField(default=0)
    nb_abonnements_actifs = models.IntegerField(default=0)
    nb_paiements = models.IntegerField(default=0)
    mrr = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    churn_rate = models.FloatField(default=0)

    genere_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rapports_mensuels'
        unique_together = ('mois', 'annee')
        ordering = ['-annee', '-mois']

    def __str__(self):
        return f"Rapport {self.mois}/{self.annee}"


class BackupBase(models.Model):
    """Backups de la base de donnees"""
    nom = models.CharField(max_length=200)
    fichier = models.FileField(upload_to='backups/')
    taille_mo = models.FloatField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'backups_base'
        ordering = ['-created_at']
