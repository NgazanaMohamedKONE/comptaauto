from django.urls import path
from . import views
urlpatterns = [
    path('', views.reporting_index, name='reporting_index'),
    path('bilan/', views.voir_bilan, name='voir_bilan'),
    path('compte-resultat/', views.voir_compte_resultat, name='voir_compte_resultat'),
    path('grand-livre/', views.voir_grand_livre, name='voir_grand_livre'),
    path('bilan/pdf/', views.export_bilan, name='export_bilan_pdf'),
    path('grand-livre/excel/', views.export_grand_livre, name='export_grand_livre_excel'),
]
