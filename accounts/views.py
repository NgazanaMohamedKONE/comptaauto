from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import User, Entreprise

def login_view(request):
    if request.user.is_authenticated:
        return redirect('admin_dashboard' if request.user.is_super_admin else 'dashboard')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('email'), password=request.POST.get('password'))
        if user:
            auth_login(request, user)
            return redirect('admin_dashboard' if user.is_super_admin else 'dashboard')
        messages.error(request, "Email ou mot de passe incorrect.")
    return render(request, 'accounts/login.html')


def register_view(request):
    if request.method == 'POST':
        if request.POST.get('password') != request.POST.get('password_confirm'):
            messages.error(request, "Mots de passe differents.")
            return render(request, 'accounts/register.html')
        if User.objects.filter(email=request.POST.get('email')).exists():
            messages.error(request, "Email deja utilise.")
            return render(request, 'accounts/register.html')

        user = User.objects.create_user(
            email=request.POST.get('email'), username=request.POST.get('username'),
            password=request.POST.get('password'), first_name=request.POST.get('first_name',''),
            last_name=request.POST.get('last_name',''), telephone=request.POST.get('telephone',''),
            role=User.Role.ENTREPRISE)
        entreprise = Entreprise.objects.create(
            nom=request.POST.get('nom_entreprise'), secteur=request.POST.get('secteur'),
            email_contact=user.email, responsable=user)

        # Creer abonnement Freemium automatique de 7 jours
        try:
            from abonnements.models import Forfait, Abonnement, Paiement, init_forfaits
            if not Forfait.objects.exists():
                init_forfaits()
            freemium = Forfait.objects.get(code='FREEMIUM')
            paiement = Paiement.objects.create(
                entreprise=entreprise, forfait=freemium,
                montant=0, methode='ESPECES',
                statut='VALIDE', paye_par=user,
                valide_at=timezone.now(),
                notes='Activation automatique Freemium a l\'inscription',
            )
            abo = Abonnement.objects.create(
                entreprise=entreprise, forfait=freemium,
                date_fin=timezone.now() + timedelta(days=7),
                statut='ACTIF',
            )
            paiement.abonnement = abo
            paiement.save()
            messages.success(request,
                "Compte cree ! Vous beneficiez de 7 jours d'essai gratuit. Connectez-vous.")
        except Exception as e:
            print(f"Erreur init freemium: {e}")
            messages.success(request, "Compte cree ! Connectez-vous.")

        return redirect('login')
    return render(request, 'accounts/register.html')


def logout_view(request):
    auth_logout(request)
    return redirect('login')


def load_demo(request):
    from django.utils import timezone
    from datetime import timedelta
    if not User.objects.filter(email='admin@comptaauto.ci').exists():
        User.objects.create_user(email='admin@comptaauto.ci', username='admin', password='Admin2026!',
            first_name='KONE', last_name="N'GAZANA MOHAMED", role=User.Role.SUPER_ADMIN, is_staff=True, is_superuser=True)
    if not User.objects.filter(email='jeancome@jkof.ci').exists():
        u = User.objects.create_user(email='jeancome@jkof.ci', username='jeancome', password='Demo2026!',
            first_name='MR JEAN', last_name='COME', role=User.Role.ENTREPRISE)
        entreprise = Entreprise.objects.create(nom='JKOF CONSULTING', secteur='BTP',
            email_contact='zanamohamedkone@gmail.com', responsable=u)

        # Donner un Pro de demo
        try:
            from abonnements.models import Forfait, Abonnement, init_forfaits
            if not Forfait.objects.exists():
                init_forfaits()
            pro = Forfait.objects.get(code='PRO')
            Abonnement.objects.create(
                entreprise=entreprise, forfait=pro,
                date_fin=timezone.now() + timedelta(days=30),
                statut='ACTIF',
            )
        except Exception as e:
            print(f"Erreur: {e}")

    messages.success(request, "Demo OK ! Admin: admin@comptaauto.ci/Admin2026! | Entreprise: jeancome@jkof.ci/Demo2026!")
    return redirect('login')
