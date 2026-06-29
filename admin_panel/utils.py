"""Utilitaires pour l'admin"""
from .models import LogAudit


def log_action(request, action, description, objet=None):
    """Cree un log d'audit"""
    try:
        LogAudit.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=action,
            objet_type=objet.__class__.__name__ if objet else '',
            objet_id=str(objet.pk) if objet else '',
            description=description,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
    except Exception as e:
        print(f"Erreur log: {e}")


def get_client_ip(request):
    """Recupere l'IP du client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')
