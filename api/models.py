"""
api/models.py
Modèles de données de la bibliothèque.

Modèles :
  - Tag            : étiquette libre pour les livres (M2M)
  - Auteur         : auteur de livres
  - Livre          : livre (FK vers Auteur, M2M vers Tag)
  - Emprunt        : emprunt d'un livre par un utilisateur
  - ProfilLecteur  : profil étendu de l'utilisateur (OneToOne)
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


# ─────────────────────────────────────────────────────────
# Tag
# ─────────────────────────────────────────────────────────
class Tag(models.Model):
    """Étiquette libre pouvant être associée à plusieurs livres."""

    nom = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Nom du tag'
    )

    def __str__(self):
        return self.nom

    class Meta:
        ordering = ['nom']
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'


# ─────────────────────────────────────────────────────────
# Auteur
# ─────────────────────────────────────────────────────────
class Auteur(models.Model):
    """Représente un auteur de livres."""

    nom = models.CharField(
        max_length=200,
        verbose_name='Nom complet'
    )
    biographie = models.TextField(
        blank=True,
        null=True,
        verbose_name='Biographie'
    )
    nationalite = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Nationalité'
    )
    date_naissance = models.DateField(
        null=True,
        blank=True,
        verbose_name='Date de naissance'
    )
    # Rempli automatiquement à la création
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Créé le'
    )
    # Qui a créé cet auteur dans le système
    cree_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auteurs_crees',
        verbose_name='Créé par'
    )

    def __str__(self):
        return self.nom

    class Meta:
        ordering = ['nom']
        verbose_name = 'Auteur'
        verbose_name_plural = 'Auteurs'


# ─────────────────────────────────────────────────────────
# Livre
# ─────────────────────────────────────────────────────────
class Livre(models.Model):
    """Représente un livre. Relié à un Auteur (FK) et des Tags (M2M)."""

    CATEGORIES = [
        ('roman',       'Roman'),
        ('essai',       'Essai'),
        ('poesie',      'Poésie'),
        ('bd',          'Bande dessinée'),
        ('science',     'Science'),
        ('histoire',    'Histoire'),
        ('philosophie', 'Philosophie'),
        ('jeunesse',    'Jeunesse'),
    ]

    titre = models.CharField(
        max_length=300,
        verbose_name='Titre'
    )
    isbn = models.CharField(
        max_length=17,
        unique=True,
        verbose_name='ISBN'
    )
    annee_publication = models.IntegerField(
        validators=[
            MinValueValidator(1000),
            MaxValueValidator(2100)
        ],
        verbose_name='Année de publication'
    )
    categorie = models.CharField(
        max_length=20,
        choices=CATEGORIES,
        default='roman',
        verbose_name='Catégorie'
    )
    resume = models.TextField(
        blank=True,
        default='',
        verbose_name='Résumé'
    )

    # ── Relations ──────────────────────────────────────────
    # ForeignKey : N livres → 1 auteur
    # CASCADE : si l'auteur est supprimé, ses livres aussi
    auteur = models.ForeignKey(
        Auteur,
        on_delete=models.CASCADE,
        related_name='livres',   # auteur.livres.all()
        verbose_name='Auteur'
    )
    # ManyToMany : un livre peut avoir plusieurs tags
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='livres',   # tag.livres.all()
        verbose_name='Tags'
    )

    # ── Disponibilité ──────────────────────────────────────
    disponible = models.BooleanField(
        default=True,
        verbose_name='Disponible'
    )

    # ── Suivi ──────────────────────────────────────────────
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Ajouté le'
    )
    cree_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='livres_crees',
        verbose_name='Ajouté par'
    )

    def __str__(self):
        return f'{self.titre} ({self.annee_publication})'

    class Meta:
        ordering = ['-annee_publication', 'titre']
        verbose_name = 'Livre'
        verbose_name_plural = 'Livres'


# ─────────────────────────────────────────────────────────
# Emprunt
# ─────────────────────────────────────────────────────────
class Emprunt(models.Model):
    """Enregistre l'emprunt d'un livre par un utilisateur."""

    utilisateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='emprunts',
        verbose_name='Lecteur'
    )
    livre = models.ForeignKey(
        Livre,
        on_delete=models.CASCADE,
        related_name='emprunts',
        verbose_name='Livre'
    )
    date_emprunt = models.DateField(
        auto_now_add=True,
        verbose_name="Date d'emprunt"
    )
    date_retour_prevue = models.DateField(
        verbose_name='Retour prévu le'
    )
    date_retour_effectif = models.DateField(
        null=True,
        blank=True,
        verbose_name='Retour effectif'
    )
    rendu = models.BooleanField(
        default=False,
        verbose_name='Rendu'
    )
    notes = models.TextField(
        blank=True,
        default='',
        verbose_name='Notes'
    )

    def __str__(self):
        statut = '✓' if self.rendu else '⏳'
        return f'{statut} {self.utilisateur.username} → {self.livre.titre}'

    class Meta:
        ordering = ['-date_emprunt']
        verbose_name = 'Emprunt'
        verbose_name_plural = 'Emprunts'


# ─────────────────────────────────────────────────────────
# ProfilLecteur
# ─────────────────────────────────────────────────────────
class ProfilLecteur(models.Model):
    """Profil étendu associé à chaque utilisateur (OneToOne)."""

    # OneToOne : 1 profil par utilisateur
    utilisateur = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profil',
        verbose_name='Utilisateur'
    )
    adresse = models.TextField(
        blank=True,
        default='',
        verbose_name='Adresse'
    )
    telephone = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name='Téléphone'
    )
    date_naissance = models.DateField(
        null=True,
        blank=True,
        verbose_name='Date de naissance'
    )
    # ManyToMany : livres favoris du lecteur
    livres_favoris = models.ManyToManyField(
        Livre,
        blank=True,
        related_name='fans',
        verbose_name='Livres favoris'
    )
    date_inscription = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Inscrit le'
    )

    def __str__(self):
        return f'Profil de {self.utilisateur.username}'

    class Meta:
        verbose_name = 'Profil lecteur'
        verbose_name_plural = 'Profils lecteurs'