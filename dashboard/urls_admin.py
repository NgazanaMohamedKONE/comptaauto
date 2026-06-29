from django.urls import path
from . import views
urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('suspendre/<int:pk>/', views.suspendre, name='suspendre'),
    path('supprimer/<int:pk>/', views.supprimer, name='supprimer'),
]
