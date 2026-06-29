from django.urls import path, include
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard_admin, name='admin_dashboard'),
    path('api/stats/', views.stats_data, name='admin_stats_data'),

    # Utilisateurs
    path('users/', views.users_list, name='admin_users_list'),
    path('users/create/', views.user_create, name='admin_user_create'),
    path('users/<int:pk>/', views.user_detail, name='admin_user_detail'),
    path('users/<int:pk>/edit/', views.user_edit, name='admin_user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='admin_user_delete'),
    path('users/<int:pk>/reset-password/', views.user_reset_password, name='admin_user_reset_password'),
    path('users/<int:pk>/toggle-active/', views.user_toggle_active, name='admin_user_toggle_active'),
    path('users/<int:pk>/impersonate/', views.user_impersonate, name='admin_user_impersonate'),
    path('stop-impersonate/', views.stop_impersonate, name='admin_stop_impersonate'),

    # Entreprises
    path('entreprises/', views.entreprises_list, name='admin_entreprises_list'),
    path('entreprises/<int:pk>/', views.entreprise_detail, name='admin_entreprise_detail'),
    path('entreprises/<int:pk>/edit/', views.entreprise_edit, name='admin_entreprise_edit'),
    path('entreprises/<int:pk>/note/', views.ajouter_note, name='admin_ajouter_note'),
    path('notes/<int:pk>/delete/', views.supprimer_note, name='admin_supprimer_note'),
    path('entreprises/<int:pk>/tag/', views.ajouter_tag_entreprise, name='admin_ajouter_tag_entreprise'),
    path('entreprise-tags/<int:pk>/delete/', views.retirer_tag_entreprise, name='admin_retirer_tag_entreprise'),

    # Tags
    path('tags/', views.tags_list, name='admin_tags_list'),
    path('tags/<int:pk>/delete/', views.tag_delete, name='admin_tag_delete'),

    # Finances
    path('finances/', views.finances_dashboard, name='admin_finances'),

    # Logs
    path('logs/', views.logs_list, name='admin_logs_list'),

    # Exports
    path('export/entreprises-csv/', views.export_entreprises_csv, name='admin_export_entreprises_csv'),
    path('export/paiements-excel/', views.export_paiements_excel, name='admin_export_paiements_excel'),

    # Pack 2
    path('pack2/', include('admin_panel.urls_pack2')),
]
