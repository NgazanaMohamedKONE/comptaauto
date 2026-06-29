from django.urls import path
from . import views
urlpatterns = [
    path('', views.rapprochement_page, name='rapprochement_page'),
    path('import/', views.import_releve, name='import_releve'),
    path('releve/<int:pk>/', views.detail_releve, name='detail_releve'),
    path('valider/<int:op_id>/', views.valider_rapprochement, name='valider_rapprochement'),
    path('modele-csv/', views.telecharger_modele, name='modele_csv'),
]
