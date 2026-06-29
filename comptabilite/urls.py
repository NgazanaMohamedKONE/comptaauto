from django.urls import path
from . import views
urlpatterns = [
    path('ecritures/', views.ecritures, name='ecritures'),
    path('ecritures/nouvelle/', views.nouvelle_ecriture, name='nouvelle_ecriture'),
    path('init-plan/', views.init_plan, name='init_plan'),
]
