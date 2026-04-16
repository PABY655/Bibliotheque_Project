"""
URLs racines du projet.
Inclut les routes API, JWT et la documentation Swagger/ReDoc.
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView      # ← ajoute cette ligne
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # Redirige / vers /api/docs/ automatiquement
    path('', RedirectView.as_view(url='/api/docs/')),  # ← ajoute cette ligne

    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]