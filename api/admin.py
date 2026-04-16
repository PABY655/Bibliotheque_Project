"""
api/admin.py
Enregistrement des modèles dans l'interface d'administration.
"""

from django.contrib import admin
from .models import Tag, Auteur, Livre, Emprunt, ProfilLecteur



@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display  = ['nom', 'nombre_livres']
    search_fields = ['nom']

    def nombre_livres(self, obj):
        return obj.livres.count()
    nombre_livres.short_description = 'Livres'


@admin.register(Auteur)
class AuteurAdmin(admin.ModelAdmin):
    list_display   = [
        'nom', 'nationalite',
        'nombre_livres', 'date_creation'
    ]
    search_fields  = ['nom', 'nationalite']
    list_filter    = ['nationalite']
    readonly_fields = ['date_creation', 'cree_par']

    def nombre_livres(self, obj):
        return obj.livres.count()
    nombre_livres.short_description = 'Livres'


@admin.register(Livre)
class LivreAdmin(admin.ModelAdmin):
    list_display   = [
        'titre', 'auteur', 'annee_publication',
        'categorie', 'disponible'
    ]
    list_filter    = ['categorie', 'disponible']
    search_fields  = ['titre', 'isbn', 'auteur__nom']
    # Widget de sélection confortable pour ManyToMany
    filter_horizontal = ['tags']
    readonly_fields   = ['date_creation', 'cree_par']
    # Modification rapide de disponible dans la liste
    list_editable     = ['disponible']


@admin.register(Emprunt)
class EmpruntAdmin(admin.ModelAdmin):
    list_display  = [
        'utilisateur', 'livre',
        'date_emprunt', 'date_retour_prevue', 'rendu'
    ]
    list_filter   = ['rendu', 'date_emprunt']
    search_fields = ['utilisateur__username', 'livre__titre']
    readonly_fields = ['date_emprunt']
    date_hierarchy  = 'date_emprunt'


@admin.register(ProfilLecteur)
class ProfilLecteurAdmin(admin.ModelAdmin):
    list_display  = [
        'utilisateur', 'telephone',
        'nombre_favoris', 'date_inscription'
    ]
    search_fields    = [
        'utilisateur__username',
        'utilisateur__email'
    ]
    filter_horizontal = ['livres_favoris']
    readonly_fields   = ['date_inscription']

    def nombre_favoris(self, obj):
        return obj.livres_favoris.count()
    nombre_favoris.short_description = 'Favoris'