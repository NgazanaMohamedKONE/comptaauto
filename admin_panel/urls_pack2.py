from django.urls import path
from . import views_pack2

urlpatterns = [
    # Configuration
    path('config/', views_pack2.config_plateforme, name='admin_config_plateforme'),
    path('forfaits/', views_pack2.gestion_forfaits, name='admin_gestion_forfaits'),
    path('forfaits/<int:pk>/edit/', views_pack2.modifier_forfait, name='admin_modifier_forfait'),

    # Coupons
    path('coupons/', views_pack2.coupons_list, name='admin_coupons_list'),
    path('coupons/create/', views_pack2.coupon_create, name='admin_coupon_create'),
    path('coupons/<int:pk>/delete/', views_pack2.coupon_delete, name='admin_coupon_delete'),
    path('coupons/<int:pk>/toggle/', views_pack2.coupon_toggle, name='admin_coupon_toggle'),

    # Campagnes
    path('campagnes/', views_pack2.campagnes_list, name='admin_campagnes_list'),
    path('campagnes/create/', views_pack2.campagne_create, name='admin_campagne_create'),
    path('campagnes/<int:pk>/', views_pack2.campagne_detail, name='admin_campagne_detail'),
    path('campagnes/<int:pk>/envoyer/', views_pack2.campagne_envoyer, name='admin_campagne_envoyer'),

    # Stats avancees
    path('stats-avancees/', views_pack2.stats_avancees, name='admin_stats_avancees'),

    # Rapports
    path('rapports/', views_pack2.rapports_list, name='admin_rapports_list'),
    path('rapports/generer/', views_pack2.generer_rapport_mensuel, name='admin_generer_rapport'),

    # Backups
    path('backups/', views_pack2.backups_list, name='admin_backups_list'),
    path('backups/creer/', views_pack2.creer_backup, name='admin_creer_backup'),
    path('backups/<int:pk>/telecharger/', views_pack2.telecharger_backup, name='admin_telecharger_backup'),
    path('backups/<int:pk>/delete/', views_pack2.supprimer_backup, name='admin_supprimer_backup'),
]
