from django.urls import path
from . import views
urlpatterns = [
    path('', views.dashboard_index, name='dashboard'),
    path('api/chart-data/', views.chart_data, name='chart_data'),
]
