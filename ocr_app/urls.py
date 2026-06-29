from django.urls import path
from . import views
urlpatterns = [
    path('', views.ocr_page, name='ocr_page'),
    path('upload/', views.upload_facture, name='ocr_upload'),
    path('facture/<int:pk>/', views.get_facture, name='ocr_facture_detail'),
    path('facture/<int:pk>/creer-ecriture/', views.creer_ecriture_ocr, name='ocr_creer_ecriture'),
]
