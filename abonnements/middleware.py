from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse


class AbonnementMiddleware:
    """Verifie que l'entreprise a un abonnement actif"""

    EXEMPT_URLS = [
        '/login/', '/logout/', '/register/', '/demo/',
        '/abonnements/', '/communication/', '/notifications/',
        '/django-admin/', '/static/', '/media/',
        '/admin-panel/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Super admin pas de restriction
        if request.user.is_super_admin:
            return self.get_response(request)

        # Verifier exempt URLs
        path = request.path
        for url in self.EXEMPT_URLS:
            if path.startswith(url):
                return self.get_response(request)

        # Verifier abonnement
        if hasattr(request.user, 'entreprise'):
            from .models import Abonnement
            abo = Abonnement.objects.filter(
                entreprise=request.user.entreprise, statut='ACTIF'
            ).order_by('-date_debut').first()

            if not abo:
                messages.warning(request, "Vous n'avez pas d'abonnement actif. Choisissez un forfait pour continuer.")
                return redirect('tarifs')

            if abo.verifier_et_expirer():
                messages.error(request, f"Votre abonnement {abo.forfait.nom} a expire. Renouvelez pour continuer.")
                return redirect('tarifs')

        return self.get_response(request)


def context_abonnement(request):
    """Context processor pour acceder a l'abonnement partout"""
    if not request.user.is_authenticated:
        return {}
    if request.user.is_super_admin:
        return {'is_super_admin': True}
    if hasattr(request.user, 'entreprise'):
        from .models import Abonnement
        abo = Abonnement.objects.filter(
            entreprise=request.user.entreprise, statut='ACTIF'
        ).order_by('-date_debut').first()
        return {'abonnement_actif': abo}
    return {}
