from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', lambda r: redirect('login')),
    path('', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('admin-panel/', include('admin_panel.urls')),
    path('comptabilite/', include('comptabilite.urls')),
    path('ocr/', include('ocr_app.urls')),
    path('rapprochement/', include('rapprochement.urls')),
    path('reporting/', include('reporting.urls')),
    path('alertes/', include('alertes.urls')),
    path('communication/', include('communication.urls')),
    path('abonnements/', include('abonnements.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
