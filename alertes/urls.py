from django.urls import path
from . import views
urlpatterns = [
    path('', views.alertes_page, name='alertes_page'),
    path('seuil/<int:pk>/', views.modifier_seuil, name='modifier_seuil'),
    path('lue/<int:pk>/', views.marquer_lue, name='marquer_lue'),
]
