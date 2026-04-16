"""
api/filters.py
Filtres avancés pour les livres et les emprunts.

Exemples d'URL :
  GET /api/livres/?categorie=roman
  GET /api/livres/?annee_min=1900&annee_max=1950
  GET /api/livres/?titre=misérables
  GET /api/livres/?auteur_nom=hugo&disponible=true
  GET /api/livres/?tag=classique
  GET /api/emprunts/?rendu=false
  GET /api/emprunts/?retour_avant=2026-04-01
"""

# api/filters.py

import django_filters
from .models import Livre, Emprunt


class LivreFilter(django_filters.FilterSet):

    categorie = django_filters.ChoiceFilter(
        choices=Livre.CATEGORIES,
        label='Catégorie'
    )
    annee_min = django_filters.NumberFilter(
        field_name='annee_publication',
        lookup_expr='gte',
        label='Année minimum'
    )
    annee_max = django_filters.NumberFilter(
        field_name='annee_publication',
        lookup_expr='lte',
        label='Année maximum'
    )
    titre = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Titre contient'
    )
    auteur_nom = django_filters.CharFilter(
        field_name='auteur__nom',
        lookup_expr='icontains',
        label="Nom de l'auteur contient"
    )
    auteur_nationalite = django_filters.CharFilter(
        field_name='auteur__nationalite',
        lookup_expr='icontains',
        label="Nationalité de l'auteur"
    )
    disponible = django_filters.BooleanFilter(
        label='Disponible'
    )
    tag = django_filters.CharFilter(
        field_name='tags__nom',
        lookup_expr='iexact',
        label='Tag (nom exact)'
    )

    class Meta:
        model  = Livre
        fields = ['categorie', 'disponible']


class EmpruntFilter(django_filters.FilterSet):

    rendu = django_filters.BooleanFilter(
        label='Rendu'
    )
    livre_titre = django_filters.CharFilter(
        field_name='livre__titre',
        lookup_expr='icontains',
        label='Titre du livre contient'
    )
    retour_avant = django_filters.DateFilter(
        field_name='date_retour_prevue',
        lookup_expr='lte',
        label='Retour prévu avant le'
    )
    retour_apres = django_filters.DateFilter(
        field_name='date_retour_prevue',
        lookup_expr='gte',
        label='Retour prévu après le'
    )

    class Meta:
        model  = Emprunt
        fields = ['rendu']
