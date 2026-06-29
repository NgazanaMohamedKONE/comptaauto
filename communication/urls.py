from django.urls import path
from . import views

urlpatterns = [
    # Messagerie
    path('messagerie/', views.messagerie, name='messagerie'),
    path('conversation/<int:pk>/', views.conversation_detail, name='conversation_detail'),
    path('conversation/nouvelle/', views.nouvelle_conversation, name='nouvelle_conversation'),

    # Tickets
    path('tickets/', views.tickets_list, name='tickets_list'),
    path('ticket/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('ticket/nouveau/', views.nouveau_ticket, name='nouveau_ticket'),
    path('ticket/<int:pk>/statut/', views.changer_statut_ticket, name='changer_statut_ticket'),

    # Annonces
    path('annonces/', views.annonces_list, name='annonces_list'),
    path('annonces/nouvelle/', views.nouvelle_annonce, name='nouvelle_annonce'),

    # Rappels
    path('rappels/', views.rappels_list, name='rappels_list'),
    path('rappels/demander/', views.demander_rappel, name='demander_rappel'),
    path('rappels/<int:pk>/effectue/', views.marquer_rappel_effectue, name='marquer_rappel_effectue'),

    # Notifications
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:pk>/lue/', views.marquer_notif_lue, name='marquer_notif_lue'),
    path('notifications/toutes-lues/', views.marquer_toutes_lues, name='marquer_toutes_lues'),
    path('api/notifications-count/', views.notifications_count, name='notifications_count'),
]
