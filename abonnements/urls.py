from django.urls import path
from . import views

urlpatterns = [
    path('tarifs/', views.tarifs, name='tarifs'),
    path('mon-abonnement/', views.mon_abonnement, name='mon_abonnement'),
    path('souscrire/<str:forfait_code>/', views.souscrire, name='souscrire'),
    path('facture/<int:pk>/pdf/', views.telecharger_facture, name='telecharger_facture'),

    # Admin
    path('admin/paiements/', views.admin_paiements, name='admin_paiements'),
    path('admin/paiements/<int:pk>/valider/', views.valider_paiement, name='valider_paiement'),
    path('admin/paiements/<int:pk>/refuser/', views.refuser_paiement, name='refuser_paiement'),
    path('admin/abonnements/', views.admin_abonnements, name='admin_abonnements'),
]
