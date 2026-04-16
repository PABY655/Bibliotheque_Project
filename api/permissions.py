"""
api/permissions.py
Permissions personnalisées pour l'API.

Classes :
  - EstProprietaireOuReadOnly : lecture libre, écriture propriétaire/admin
  - EstAdminOuReadOnly        : lecture libre, écriture admin uniquement
  - EstAuthentifieOuLecture   : lecture libre, écriture authentifiée
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


# ─────────────────────────────────────────────────────────
# Permission 1 : Propriétaire ou lecture seule
# ─────────────────────────────────────────────────────────
class EstProprietaireOuReadOnly(BasePermission):
    """
    Permission à deux niveaux :

      - Lecture (GET, HEAD, OPTIONS) : autorisée pour TOUS.
      - Écriture (POST, PUT, PATCH, DELETE) :
          * réservée au propriétaire (champ cree_par) de l'objet
          * ou aux administrateurs (is_staff=True)

    ⚠️  Le modèle doit avoir un champ 'cree_par'
        ForeignKey vers User.

    Exemples :
      GET  /api/livres/       → 200 OK  (anonyme)
      POST /api/livres/       → 401     (anonyme)
      POST /api/livres/       → 201     (connecté)
      PUT  /api/livres/1/     → 403     (connecté mais pas propriétaire)
      PUT  /api/livres/1/     → 200     (propriétaire ou admin)
    """

    message = (
        'Vous devez être le propriétaire ou un '
        'administrateur pour modifier cet objet.'
    )

    def has_permission(self, request, view):
        """
        Niveau VUE : vérifié avant même d'accéder à un objet.
        Lecture = libre / Écriture = doit être connecté.
        """
        # GET, HEAD, OPTIONS → autorisé pour tous
        if request.method in SAFE_METHODS:
            return True
        # POST, PUT, PATCH, DELETE → doit être authentifié
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        """
        Niveau OBJET : vérifié lors d'un accès à un objet
        spécifique via get_object().

        Appelé APRÈS has_permission().
        """
        # Lecture toujours autorisée
        if request.method in SAFE_METHODS:
            return True

        # Les admins peuvent tout faire
        if request.user.is_staff:
            return True

        # Seul le propriétaire peut modifier
        return getattr(obj, 'cree_par', None) == request.user


# ─────────────────────────────────────────────────────────
# Permission 2 : Admin ou lecture seule
# ─────────────────────────────────────────────────────────
class EstAdminOuReadOnly(BasePermission):
    """
    Lecture libre pour tous.
    Écriture réservée aux administrateurs (is_staff=True).

    Utile pour : Tags, Catégories, données de référence.

    Exemples :
      GET  /api/tags/    → 200 OK  (anonyme)
      POST /api/tags/    → 401     (anonyme)
      POST /api/tags/    → 403     (connecté mais pas admin)
      POST /api/tags/    → 201     (admin)
    """

    message = (
        'Seuls les administrateurs peuvent '
        'modifier ces données.'
    )

    def has_permission(self, request, view):
        # Lecture libre
        if request.method in SAFE_METHODS:
            return True
        # Écriture : admin uniquement
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )


# ─────────────────────────────────────────────────────────
# Permission 3 : Authentifié ou lecture seule
# ─────────────────────────────────────────────────────────
class EstAuthentifieOuLecture(BasePermission):
    """
    Lecture libre pour tous.
    Écriture pour tout utilisateur authentifié.

    Alias explicite d'IsAuthenticatedOrReadOnly
    avec message personnalisé en français.

    Exemples :
      GET  /api/auteurs/   → 200 OK  (anonyme)
      POST /api/auteurs/   → 401     (anonyme)
      POST /api/auteurs/   → 201     (connecté, quel que soit le rôle)
    """

    message = (
        'Vous devez être connecté pour '
        'effectuer cette action.'
    )

    def has_permission(self, request, view):
        # Lecture libre
        if request.method in SAFE_METHODS:
            return True
        # Écriture : doit être authentifié
        return bool(request.user and request.user.is_authenticated)
SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')
# Ces méthodes ne modifient jamais les données
# → toujours autorisées en lecture publique


