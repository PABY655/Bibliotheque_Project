"""
api/views.py
ViewSets et vues de l'API bibliothèque.

Structure :
  - TagViewSet          : CRUD tags (admin pour écriture)
  - AuteurViewSet       : CRUD auteurs + livres, stats
  - LivreViewSet        : CRUD livres + disponibles, emprunter, rendre
  - EmpruntViewSet      : CRUD emprunts (filtrés par utilisateur)
  - ProfilLecteurView   : Profil de l'utilisateur connecté
  - InscriptionView     : Création de compte
"""

from django.utils import timezone
from django.db.models import Count

from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny,
    IsAdminUser,
)
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Tag, Auteur, Livre, Emprunt, ProfilLecteur
from .serializers import (
    TagSerializer,
    AuteurListSerializer,
    AuteurSerializer,
    LivreListSerializer,
    LivreSerializer,
    EmpruntSerializer,
    ProfilLecteurSerializer,
    InscriptionSerializer,
)
from .permissions import EstProprietaireOuReadOnly, EstAdminOuReadOnly
from .filters import LivreFilter, EmpruntFilter
from .pagination import StandardPagination


# ─────────────────────────────────────────────────────────
# Tag ViewSet
# ─────────────────────────────────────────────────────────
@extend_schema_view(
    list=extend_schema(summary="Liste tous les tags"),
    create=extend_schema(summary="Créer un tag (admin)"),
    retrieve=extend_schema(summary="Détail d'un tag"),
    update=extend_schema(summary="Modifier un tag (admin)"),
    destroy=extend_schema(summary="Supprimer un tag (admin)"),
)
class TagViewSet(viewsets.ModelViewSet):
    """
    CRUD pour les tags.
    Lecture publique, écriture réservée aux administrateurs.
    """

    # annotate : ajoute nb_livres sans requête supplémentaire
    queryset = Tag.objects.annotate(
        nb_livres=Count('livres')
    ).order_by('nom')

    serializer_class   = TagSerializer
    permission_classes = [EstAdminOuReadOnly]
    filter_backends    = [SearchFilter]
    search_fields      = ['nom']
    # Pas de pagination pour les tags (petite liste stable)
    pagination_class   = None


# ─────────────────────────────────────────────────────────
# Auteur ViewSet
# ─────────────────────────────────────────────────────────
@extend_schema_view(
    list=extend_schema(summary="Liste des auteurs"),
    create=extend_schema(summary="Créer un auteur"),
    retrieve=extend_schema(summary="Détail d'un auteur"),
    update=extend_schema(summary="Modifier un auteur"),
    destroy=extend_schema(summary="Supprimer un auteur"),
)
class AuteurViewSet(viewsets.ModelViewSet):
    """
    CRUD complet pour les auteurs.

    Actions personnalisées :
      GET /api/auteurs/{id}/livres/ → livres de cet auteur
      GET /api/auteurs/stats/       → statistiques globales
    """

    queryset = Auteur.objects.prefetch_related('livres').all()
    permission_classes = [EstProprietaireOuReadOnly]
    filter_backends    = [SearchFilter, OrderingFilter]
    search_fields      = ['nom', 'nationalite', 'biographie']
    ordering_fields    = ['nom', 'nationalite', 'date_creation']
    ordering           = ['nom']
    pagination_class   = StandardPagination

    def get_serializer_class(self):
        """
        Sérialiseur allégé pour la liste,
        complet pour le détail.
        """
        if self.action == 'list':
            return AuteurListSerializer
        return AuteurSerializer

    def perform_create(self, serializer):
        """Enregistre l'utilisateur connecté comme créateur."""
        serializer.save(cree_par=self.request.user)

    # ── Action : livres d'un auteur ────────────────────────
    @extend_schema(
        summary="Livres d'un auteur",
        responses=LivreListSerializer(many=True)
    )
    @action(detail=True, methods=['get'], url_path='livres')
    def livres(self, request, pk=None):
        """
        Retourne tous les livres d'un auteur donné.
        Paramètre optionnel : ?disponible=true
        """
        auteur   = self.get_object()
        livres_qs = (
            auteur.livres
            .select_related('auteur')
            .prefetch_related('tags')
            .all()
        )

        # Filtre optionnel sur la disponibilité
        disponible = request.query_params.get('disponible')
        if disponible is not None:
            livres_qs = livres_qs.filter(
                disponible=disponible.lower() == 'true'
            )

        # Pagination
        page = self.paginate_queryset(livres_qs)
        if page is not None:
            serializer = LivreListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = LivreListSerializer(livres_qs, many=True)
        return Response(serializer.data)

    # ── Action : statistiques globales ────────────────────
    @extend_schema(summary="Statistiques globales")
    @action(
        detail=False,
        methods=['get'],
        permission_classes=[AllowAny]
    )
    def stats(self, request):
        """
        Statistiques générales :
        totaux, top auteurs, répartition par catégorie.
        """
        data = {
            'totaux': {
                'auteurs': Auteur.objects.count(),
                'livres': Livre.objects.count(),
                'livres_disponibles': Livre.objects.filter(
                    disponible=True
                ).count(),
                'emprunts_en_cours': Emprunt.objects.filter(
                    rendu=False
                ).count(),
                'tags': Tag.objects.count(),
            },
            'top_auteurs': list(
                Auteur.objects
                .annotate(nb=Count('livres'))
                .order_by('-nb')[:5]
                .values('id', 'nom', 'nb')
            ),
            'repartition_categories': list(
                Livre.objects
                .values('categorie')
                .annotate(nb=Count('id'))
                .order_by('-nb')
            ),
            'nationalites': list(
                Auteur.objects
                .exclude(nationalite='')
                .values_list('nationalite', flat=True)
                .distinct()
                .order_by('nationalite')
            ),
        }
        return Response(data)


# ─────────────────────────────────────────────────────────
# Livre ViewSet
# ─────────────────────────────────────────────────────────
@extend_schema_view(
    list=extend_schema(
        summary="Liste des livres (paginée, filtrée)"
    ),
    create=extend_schema(summary="Ajouter un livre"),
    retrieve=extend_schema(summary="Détail d'un livre"),
    update=extend_schema(summary="Modifier un livre"),
    partial_update=extend_schema(
        summary="Modification partielle d'un livre"
    ),
    destroy=extend_schema(summary="Supprimer un livre"),
)
class LivreViewSet(viewsets.ModelViewSet):
    """
    CRUD complet pour les livres.

    Actions personnalisées :
      GET  /api/livres/disponibles/    → livres disponibles
      POST /api/livres/{id}/emprunter/ → emprunter un livre
      POST /api/livres/{id}/rendre/    → rendre un livre
    """

    # ── Optimisation SQL ───────────────────────────────────
    # select_related  → JOIN pour ForeignKey  (auteur, cree_par)
    # prefetch_related → requête séparée pour ManyToMany (tags)
    # Sans ces optimisations : problème N+1
    # (1 requête par livre pour charger l'auteur = très lent)
    queryset = (
        Livre.objects
        .select_related('auteur', 'cree_par')
        .prefetch_related('tags')
        .all()
    )

    permission_classes = [EstProprietaireOuReadOnly]
    pagination_class   = StandardPagination
    filterset_class    = LivreFilter
    filter_backends    = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]
    search_fields   = ['titre', 'auteur__nom', 'isbn', 'resume']
    ordering_fields = [
        'titre', 'annee_publication',
        'date_creation', 'auteur__nom'
    ]
    ordering = ['-date_creation']

    def get_serializer_class(self):
        """Sérialiseur allégé pour la liste, complet sinon."""
        if self.action == 'list':
            return LivreListSerializer
        return LivreSerializer

    def perform_create(self, serializer):
        """Enregistre l'utilisateur connecté comme créateur."""
        serializer.save(cree_par=self.request.user)

    # ── Action : livres disponibles ────────────────────────
    @extend_schema(summary="Livres disponibles à l'emprunt")
    @action(
        detail=False,
        methods=['get'],
        url_path='disponibles',
        permission_classes=[AllowAny]
    )
    def disponibles(self, request):
        """
        Retourne uniquement les livres disponibles.
        Supporte les mêmes filtres et tri que la liste principale.
        """
        qs = self.get_queryset().filter(disponible=True)
        # Applique aussi les filtres et le tri
        qs = self.filter_queryset(qs)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = LivreListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = LivreListSerializer(qs, many=True)
        return Response(serializer.data)

    # ── Action : emprunter un livre ────────────────────────
    @extend_schema(summary="Emprunter un livre")
    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def emprunter(self, request, pk=None):
        """
        Marque le livre comme non disponible
        et crée un enregistrement d'emprunt.

        Corps attendu :
        { "date_retour_prevue": "2026-04-30" }
        """
        livre = self.get_object()

        # Vérification 1 : livre disponible ?
        if not livre.disponible:
            return Response(
                {
                    'erreur': (
                        f'Le livre "{livre.titre}" '
                        f'n\'est pas disponible.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérification 2 : déjà emprunté par cet utilisateur ?
        deja_emprunte = Emprunt.objects.filter(
            utilisateur=request.user,
            livre=livre,
            rendu=False
        ).exists()

        if deja_emprunte:
            return Response(
                {
                    'erreur': (
                        'Vous avez déjà ce livre '
                        'en cours d\'emprunt.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérification 3 : date de retour fournie ?
        date_retour = request.data.get('date_retour_prevue')
        if not date_retour:
            return Response(
                {
                    'erreur': (
                        '"date_retour_prevue" est requis '
                        '(format : YYYY-MM-DD).'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validation via le sérialiseur
        serializer = EmpruntSerializer(
            data={
                'livre_id': livre.pk,
                'date_retour_prevue': date_retour,
            },
            context={'request': request},
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Sauvegarde : crée l'emprunt + marque le livre indisponible
        emprunt          = serializer.save(utilisateur=request.user)
        livre.disponible = False
        livre.save(update_fields=['disponible'])

        return Response(
            {
                'message': (
                    f'Livre "{livre.titre}" '
                    f'emprunté avec succès.'
                ),
                'emprunt_id':    emprunt.pk,
                'retour_prevu':  str(emprunt.date_retour_prevue),
            },
            status=status.HTTP_201_CREATED,
        )

    # ── Action : rendre un livre ───────────────────────────
    @extend_schema(summary="Rendre un livre emprunté")
    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def rendre(self, request, pk=None):
        """
        Marque l'emprunt comme rendu
        et rend le livre disponible à nouveau.
        """
        livre = self.get_object()

        # Trouver l'emprunt actif de cet utilisateur
        emprunt = Emprunt.objects.filter(
            utilisateur=request.user,
            livre=livre,
            rendu=False
        ).first()

        if not emprunt:
            return Response(
                {
                    'erreur': (
                        'Aucun emprunt actif trouvé '
                        'pour ce livre.'
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Mettre à jour l'emprunt
        emprunt.rendu                = True
        emprunt.date_retour_effectif = timezone.now().date()
        emprunt.save(
            update_fields=['rendu', 'date_retour_effectif']
        )

        # Rendre le livre disponible
        livre.disponible = True
        livre.save(update_fields=['disponible'])

        return Response({
            'message': (
                f'Livre "{livre.titre}" '
                f'rendu avec succès.'
            ),
            'date_retour_effectif': str(
                emprunt.date_retour_effectif
            ),
        })


# ─────────────────────────────────────────────────────────
# Emprunt ViewSet
# ─────────────────────────────────────────────────────────
class EmpruntViewSet(viewsets.ModelViewSet):
    """
    Gestion des emprunts.
    Chaque utilisateur ne voit QUE ses propres emprunts.
    Les admins voient tous les emprunts.
    """

    serializer_class   = EmpruntSerializer
    permission_classes = [IsAuthenticated]
    filterset_class    = EmpruntFilter
    filter_backends    = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]
    search_fields   = ['livre__titre', 'notes']
    ordering_fields = [
        'date_emprunt',
        'date_retour_prevue',
        'rendu'
    ]
    ordering         = ['-date_emprunt']
    pagination_class = StandardPagination

    def get_queryset(self):
        """
        Filtre automatique :
        - Utilisateur normal → ses emprunts uniquement
        - Admin              → tous les emprunts
        """
        user = self.request.user
        qs = (
            Emprunt.objects
            .select_related('livre', 'utilisateur')
            .prefetch_related('livre__tags')
        )
        if user.is_staff:
            return qs.all()
        return qs.filter(utilisateur=user)

    def perform_create(self, serializer):
        """L'utilisateur connecté est automatiquement le lecteur."""
        serializer.save(utilisateur=self.request.user)

    # ── Action : emprunts en retard (admin) ────────────────
    @extend_schema(summary="Emprunts en retard (admin)")
    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAdminUser]
    )
    def en_retard(self, request):
        """
        Liste les emprunts non rendus
        dont la date de retour est dépassée.
        Réservé aux administrateurs.
        """
        aujourd_hui = timezone.now().date()
        qs = Emprunt.objects.filter(
            rendu=False,
            date_retour_prevue__lt=aujourd_hui
        ).select_related('livre', 'utilisateur')

        serializer = self.get_serializer(qs, many=True)
        return Response({
            'total_en_retard': qs.count(),
            'emprunts':        serializer.data,
        })


# ─────────────────────────────────────────────────────────
# Profil Lecteur
# ─────────────────────────────────────────────────────────
class ProfilLecteurView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/profil/  → Profil de l'utilisateur connecté
    PUT   /api/profil/  → Mise à jour complète
    PATCH /api/profil/  → Mise à jour partielle
    """

    serializer_class   = ProfilLecteurSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Retourne ou crée le profil de l'utilisateur connecté."""
        profil, _ = ProfilLecteur.objects.get_or_create(
            utilisateur=self.request.user
        )
        return profil

    @extend_schema(summary="Ajouter/retirer un favori (toggle)")
    def toggle_favori(self, request):
        """
        Ajoute ou retire un livre des favoris.
        Corps : { "livre_id": 42 }
        """
        livre_id = request.data.get('livre_id')
        if not livre_id:
            return Response(
                {'erreur': '"livre_id" est requis.'},
                status=400
            )

        try:
            livre = Livre.objects.get(pk=livre_id)
        except Livre.DoesNotExist:
            return Response(
                {'erreur': 'Livre introuvable.'},
                status=404
            )

        profil, _ = ProfilLecteur.objects.get_or_create(
            utilisateur=request.user
        )

        if livre in profil.livres_favoris.all():
            profil.livres_favoris.remove(livre)
            action_str = 'retiré des'
        else:
            profil.livres_favoris.add(livre)
            action_str = 'ajouté aux'

        return Response({
            'message': (
                f'"{livre.titre}" {action_str} favoris.'
            ),
            'nombre_favoris': profil.livres_favoris.count(),
        })


# ─────────────────────────────────────────────────────────
# Inscription
# ─────────────────────────────────────────────────────────
class InscriptionView(generics.CreateAPIView):
    """
    POST /api/auth/inscription/
    Crée un compte utilisateur + profil lecteur.
    """

    serializer_class   = InscriptionSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'message': f'Compte créé. Bienvenue, {user.username} !',
                'username': user.username,
                'email': user.email,
            },
            status=status.HTTP_201_CREATED,
        )