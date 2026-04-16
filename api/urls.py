"""
api/urls.py
Configuration des routes de l'API.

Le Router génère automatiquement les URLs standard
pour chaque ViewSet. Les URLs supplémentaires
(JWT, inscription, profil) sont ajoutées manuellement.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    TagViewSet,
    AuteurViewSet,
    LivreViewSet,
    EmpruntViewSet,
    ProfilLecteurView,
    InscriptionView,
)

# ─────────────────────────────────────────────────────────
# Router automatique
# ─────────────────────────────────────────────────────────
# Génère pour chaque ViewSet :
#   GET    /api/<prefix>/         → list
#   POST   /api/<prefix>/         → create
#   GET    /api/<prefix>/{pk}/    → retrieve
#   PUT    /api/<prefix>/{pk}/    → update
#   PATCH  /api/<prefix>/{pk}/    → partial_update
#   DELETE /api/<prefix>/{pk}/    → destroy
#   + les @action personnalisées
router = DefaultRouter()
router.register(r'tags',     TagViewSet,     basename='tag')
router.register(r'auteurs',  AuteurViewSet,  basename='auteur')
router.register(r'livres',   LivreViewSet,   basename='livre')
router.register(r'emprunts', EmpruntViewSet, basename='emprunt')

# ─────────────────────────────────────────────────────────
# URLs manuelles
# ─────────────────────────────────────────────────────────
urlpatterns = [

    # ── Toutes les routes du router ───────────────────────
    path('', include(router.urls)),

    # ── Authentification JWT ──────────────────────────────
    # POST {username, password} → {access, refresh}
    path(
        'auth/token/',
        TokenObtainPairView.as_view(),
        name='token_obtain'
    ),
    # POST {refresh} → {access}
    path(
        'auth/token/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh'
    ),
    # POST {username, email, password, password2}
    path(
        'auth/inscription/',
        InscriptionView.as_view(),
        name='inscription'
    ),

    # ── Profil utilisateur connecté ───────────────────────
    # GET / PUT / PATCH
    path(
        'profil/',
        ProfilLecteurView.as_view(),
        name='profil'
    ),
    # POST {livre_id} → toggle favori
    path(
        'profil/favoris/',
        ProfilLecteurView.as_view(),
        name='profil-favoris'
    ),
]

# ─────────────────────────────────────────────────────────
# Récapitulatif de toutes les URLs générées
# ─────────────────────────────────────────────────────────
#
# AUTH
#   POST  /api/auth/inscription/          → créer un compte
#   POST  /api/auth/token/                → obtenir token JWT
#   POST  /api/auth/token/refresh/        → renouveler token
#
# TAGS
#   GET   /api/tags/                      → liste des tags
#   POST  /api/tags/                      → créer (admin)
#   GET   /api/tags/{id}/                 → détail
#   PUT   /api/tags/{id}/                 → modifier (admin)
#   DELETE /api/tags/{id}/                → supprimer (admin)
#
# AUTEURS
#   GET   /api/auteurs/                   → liste
#   POST  /api/auteurs/                   → créer (auth)
#   GET   /api/auteurs/{id}/              → détail
#   PUT   /api/auteurs/{id}/              → modifier
#   DELETE /api/auteurs/{id}/             → supprimer
#   GET   /api/auteurs/{id}/livres/       → livres de l'auteur
#   GET   /api/auteurs/stats/             → statistiques
#
# LIVRES
#   GET   /api/livres/                    → liste paginée
#   POST  /api/livres/                    → ajouter (auth)
#   GET   /api/livres/{id}/               → détail
#   PUT   /api/livres/{id}/               → modifier
#   PATCH /api/livres/{id}/               → modif partielle
#   DELETE /api/livres/{id}/              → supprimer
#   GET   /api/livres/disponibles/        → disponibles
#   POST  /api/livres/{id}/emprunter/     → emprunter (auth)
#   POST  /api/livres/{id}/rendre/        → rendre (auth)
#
# EMPRUNTS
#   GET   /api/emprunts/                  → mes emprunts
#   POST  /api/emprunts/                  → créer (auth)
#   GET   /api/emprunts/{id}/             → détail
#   PATCH /api/emprunts/{id}/             → modifier
#   DELETE /api/emprunts/{id}/            → supprimer
#   GET   /api/emprunts/en_retard/        → en retard (admin)
#
# PROFIL
#   GET   /api/profil/                    → mon profil
#   PUT   /api/profil/                    → mettre à jour
#   POST  /api/profil/favoris/            → toggle favori
