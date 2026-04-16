"""
api/serializers.py
Sérialiseurs pour tous les modèles.

Chaque sérialiseur gère :
  - La conversion modèle ↔ JSON
  - La validation des données entrantes
  - La gestion des relations (imbrication lecture, IDs écriture)
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Tag, Auteur, Livre, Emprunt, ProfilLecteur


# ─────────────────────────────────────────────────────────
# Tag
# ─────────────────────────────────────────────────────────
class TagSerializer(serializers.ModelSerializer):
    """Sérialiseur simple pour les tags."""

    # Champ calculé : nombre de livres associés au tag
    nombre_livres = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ['id', 'nom', 'nombre_livres']
        read_only_fields = ['id']

    def get_nombre_livres(self, obj):
        return obj.livres.count()

    def validate_nom(self, value):
        """Le nom du tag doit être en minuscules et sans espaces superflus."""
        return value.strip().lower()


# ─────────────────────────────────────────────────────────
# Auteur
# ─────────────────────────────────────────────────────────
class AuteurListSerializer(serializers.ModelSerializer):
    """Version allégée pour la liste des auteurs (performances)."""

    nombre_livres = serializers.SerializerMethodField()

    class Meta:
        model = Auteur
        fields = ['id', 'nom', 'nationalite', 'nombre_livres']
        read_only_fields = ['id']

    def get_nombre_livres(self, obj):
        # Utilise le prefetch_related si disponible
        # → pas de requête SQL supplémentaire
        return obj.livres.count()


class AuteurSerializer(serializers.ModelSerializer):
    """Sérialiseur complet pour le détail d'un auteur."""

    nombre_livres = serializers.SerializerMethodField()
    # Nom de l'utilisateur qui a créé l'entrée (lecture seule)
    cree_par_username = serializers.SerializerMethodField()

    class Meta:
        model = Auteur
        fields = [
            'id', 'nom', 'biographie', 'nationalite',
            'date_naissance', 'date_creation',
            'nombre_livres', 'cree_par_username',
        ]
        read_only_fields = ['id', 'date_creation', 'cree_par_username']

    def get_nombre_livres(self, obj):
        return obj.livres.count()

    def get_cree_par_username(self, obj):
        return obj.cree_par.username if obj.cree_par else None

    def validate_nom(self, value):
        """Le nom ne doit pas être vide après nettoyage."""
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError(
                "Le nom ne peut pas être vide."
            )
        return cleaned


# ─────────────────────────────────────────────────────────
# Livre
# ─────────────────────────────────────────────────────────
class LivreListSerializer(serializers.ModelSerializer):
    """Version allégée pour la liste des livres."""

    # Traversée de relation : auteur.nom directement
    auteur_nom = serializers.CharField(
        source='auteur.nom',
        read_only=True
    )
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Livre
        fields = [
            'id', 'titre', 'isbn', 'annee_publication',
            'categorie', 'disponible', 'auteur_nom', 'tags',
        ]
        read_only_fields = ['id']


class LivreSerializer(serializers.ModelSerializer):
    """
    Sérialiseur principal pour la création et mise à jour d'un livre.

    Stratégie lecture / écriture pour les relations :
      - auteur    : objet imbriqué en lecture   (read_only)
      - auteur_id : ID en écriture              (write_only)
      - tags      : objets imbriqués en lecture  (read_only)
      - tag_ids   : liste d'IDs en écriture      (write_only)
    """

    # ── Lecture ────────────────────────────────────────────
    auteur = AuteurListSerializer(read_only=True)
    tags   = TagSerializer(many=True, read_only=True)
    cree_par_username = serializers.SerializerMethodField()

    # ── Écriture ───────────────────────────────────────────
    auteur_id = serializers.PrimaryKeyRelatedField(
        queryset=Auteur.objects.all(),
        source='auteur',
        write_only=True,
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        source='tags',
        write_only=True,
        required=False,
    )

    class Meta:
        model = Livre
        fields = [
            'id', 'titre', 'isbn', 'annee_publication',
            'categorie', 'resume', 'disponible', 'date_creation',
            'auteur',    'auteur_id',   # relation auteur
            'tags',      'tag_ids',     # relation tags
            'cree_par_username',
        ]
        read_only_fields = [
            'id', 'date_creation',
            'cree_par_username', 'disponible',
        ]

    def get_cree_par_username(self, obj):
        return obj.cree_par.username if obj.cree_par else None

    # ── Validations personnalisées ─────────────────────────

    def validate_isbn(self, value):
        """L'ISBN doit contenir exactement 13 chiffres."""
        clean = value.replace('-', '').replace(' ', '')
        if not clean.isdigit() or len(clean) != 13:
            raise serializers.ValidationError(
                "L'ISBN doit contenir exactement 13 chiffres "
                "(ex: 978-2-07-036024-5)."
            )
        return value

    def validate_annee_publication(self, value):
        """L'année doit être plausible (1000 → année courante)."""
        annee_courante = timezone.now().year
        if value < 1000 or value > annee_courante:
            raise serializers.ValidationError(
                f"L'année doit être comprise entre 1000 "
                f"et {annee_courante}."
            )
        return value

    def validate(self, data):
        """
        Validation cross-champs :
        Les essais doivent avoir un auteur avec biographie.
        """
        if data.get('categorie') == 'essai':
            auteur = data.get('auteur') or (
                self.instance.auteur if self.instance else None
            )
            if auteur and not auteur.biographie:
                raise serializers.ValidationError({
                    'categorie': (
                        "Les essais requièrent une "
                        "biographie de l'auteur."
                    )
                })
        return data


# ─────────────────────────────────────────────────────────
# Emprunt
# ─────────────────────────────────────────────────────────
class EmpruntSerializer(serializers.ModelSerializer):
    """
    Sérialiseur pour les emprunts.
    L'utilisateur est injecté automatiquement depuis la vue.
    """

    # ── Lecture ────────────────────────────────────────────
    livre_titre = serializers.CharField(
        source='livre.titre',
        read_only=True
    )
    utilisateur_username = serializers.CharField(
        source='utilisateur.username',
        read_only=True
    )
    # Champ calculé : est-ce que l'emprunt est en retard ?
    est_en_retard = serializers.SerializerMethodField()

    # ── Écriture ───────────────────────────────────────────
    livre_id = serializers.PrimaryKeyRelatedField(
        queryset=Livre.objects.filter(disponible=True),
        source='livre',
        write_only=True,
    )

    class Meta:
        model = Emprunt
        fields = [
            'id', 'livre_titre', 'utilisateur_username',
            'date_emprunt', 'date_retour_prevue',
            'date_retour_effectif', 'rendu',
            'notes', 'est_en_retard',
            'livre_id',  # write_only
        ]
        read_only_fields = [
            'id', 'date_emprunt',
            'utilisateur_username',
            'livre_titre', 'est_en_retard',
        ]

    def get_est_en_retard(self, obj):
        """Retard = non rendu ET date prévue dépassée."""
        if obj.rendu:
            return False
        return timezone.now().date() > obj.date_retour_prevue

    def validate_date_retour_prevue(self, value):
        """La date de retour doit être dans le futur."""
        if value <= timezone.now().date():
            raise serializers.ValidationError(
                "La date de retour prévue doit être dans le futur."
            )
        return value

    def validate(self, data):
        """Un livre doit être disponible pour être emprunté."""
        livre = data.get('livre') or (
            self.instance.livre if self.instance else None
        )
        if livre and not livre.disponible:
            raise serializers.ValidationError({
                'livre_id': (
                    f'Le livre "{livre.titre}" '
                    f'n\'est pas disponible.'
                )
            })
        return data


# ─────────────────────────────────────────────────────────
# ProfilLecteur
# ─────────────────────────────────────────────────────────
class ProfilLecteurSerializer(serializers.ModelSerializer):
    """Sérialiseur pour le profil étendu du lecteur."""

    username        = serializers.CharField(
        source='utilisateur.username', read_only=True
    )
    email           = serializers.EmailField(
        source='utilisateur.email', read_only=True
    )
    livres_favoris  = LivreListSerializer(many=True, read_only=True)
    nombre_emprunts = serializers.SerializerMethodField()

    # Écriture : liste d'IDs de livres favoris
    favori_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Livre.objects.all(),
        source='livres_favoris',
        write_only=True,
        required=False,
    )

    class Meta:
        model = ProfilLecteur
        fields = [
            'id', 'username', 'email',
            'adresse', 'telephone', 'date_naissance',
            'date_inscription',
            'livres_favoris', 'favori_ids',
            'nombre_emprunts',
        ]
        read_only_fields = [
            'id', 'username', 'email', 'date_inscription'
        ]

    def get_nombre_emprunts(self, obj):
        return obj.utilisateur.emprunts.count()


# ─────────────────────────────────────────────────────────
# Inscription utilisateur
# ─────────────────────────────────────────────────────────
class InscriptionSerializer(serializers.ModelSerializer):
    """
    Crée un compte utilisateur + profil lecteur
    en une seule requête POST.
    """

    password  = serializers.CharField(
        write_only=True, min_length=8
    )
    password2 = serializers.CharField(
        write_only=True,
        label='Confirmation mot de passe'
    )

    class Meta:
        model  = User
        fields = [
            'username', 'email',
            'password', 'password2',
            'first_name', 'last_name'
        ]

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({
                'password2': (
                    'Les mots de passe ne correspondent pas.'
                )
            })
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        # Créer automatiquement le profil lecteur associé
        ProfilLecteur.objects.create(utilisateur=user)
        return user