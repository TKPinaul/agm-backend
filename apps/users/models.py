import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


# ─────────────────────────────────────────────
# ROLE
# ─────────────────────────────────────────────

class Role(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "role"
        verbose_name = "Rôle"
        verbose_name_plural = "Rôles"

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────
# PERMISSION
# ─────────────────────────────────────────────

class Permission(models.Model):
    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role     = models.OneToOneField(
        Role,
        on_delete=models.CASCADE,
        related_name="permission",
        db_column="role_id"
    )
    resource = models.CharField(
        max_length=100,
        help_text="Ressource concernée ex: patients, reports, users"
    )
    read     = models.BooleanField(default=False)
    write    = models.BooleanField(default=False)
    update   = models.BooleanField(default=False)
    delete   = models.BooleanField(default=False)
    download = models.BooleanField(default=False)

    class Meta:
        db_table = "permission"
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"

    def __str__(self):
        return f"Permission({self.role.name} | {self.resource})"


# ─────────────────────────────────────────────
# USER MANAGER
# ─────────────────────────────────────────────

class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # hash automatique bcrypt si configuré
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


# ─────────────────────────────────────────────
# USER
# ─────────────────────────────────────────────

class GenderChoices(models.TextChoices):
    MALE        = "M",     "Masculin"
    FEMALE      = "F",     "Féminin"
    OTHER       = "AUTRE", "Autre"
    UNSPECIFIED = "NR",    "Non renseigné"


class User(AbstractBaseUser, PermissionsMixin):
    # ── Identité ──────────────────────────────
    usid                   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email                  = models.EmailField(max_length=255, unique=True)
    first_name             = models.CharField(max_length=100)
    last_name              = models.CharField(max_length=100)
    gender                 = models.CharField(max_length=10, choices=GenderChoices.choices)
    phone_number_primal    = models.CharField(max_length=20)
    phone_number_second    = models.CharField(max_length=20, blank=True, null=True)

    # ── Rôle ──────────────────────────────────
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,   # PROTECT : empêche de supprimer un rôle encore utilisé
        related_name="users",
        null=True,
        blank=True,
        db_column="role_id"
    )

    # ── Statut du compte ──────────────────────
    is_active    = models.BooleanField(default=True)
    is_staff     = models.BooleanField(default=False)  # requis par Django admin
    email_verified_at = models.DateTimeField(null=True, blank=True)

    # ── Double authentification (2FA) ─────────
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret  = models.TextField(
        blank=True, null=True,
        help_text="Clé TOTP — doit être chiffrée au repos (ex: django-encrypted-model-fields)"
    )

    # ── Sécurité / brute force ─────────────────
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until          = models.DateTimeField(null=True, blank=True)

    # ── Réinitialisation du mot de passe ──────
    password_reset_token   = models.CharField(max_length=255, blank=True, null=True)
    password_reset_expires = models.DateTimeField(null=True, blank=True)

    # ── Traçabilité connexion ──────────────────
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    # ── Timestamps ────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)  # soft delete

    # ── Configuration Django ───────────────────
    USERNAME_FIELD  = "email"   # connexion par email
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        db_table = "users"
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
            models.Index(fields=["last_login_at"]),
            models.Index(fields=["deleted_at"]),  # index partiel via migration manuelle
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"

    # ── Helpers ───────────────────────────────

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_locked(self):
        """Vérifie si le compte est verrouillé suite à trop d'échecs."""
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    @property
    def is_deleted(self):
        """Soft delete — True si le compte a été supprimé logiquement."""
        return self.deleted_at is not None

    def soft_delete(self):
        """Suppression logique du compte."""
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["deleted_at", "is_active"])

    def increment_failed_login(self, max_attempts=5, lockout_minutes=15):
        """Incrémente les échecs et verrouille si le seuil est atteint."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=lockout_minutes)
        self.save(update_fields=["failed_login_attempts", "locked_until"])

    def reset_failed_login(self):
        """Remet le compteur à zéro après une connexion réussie."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=["failed_login_attempts", "locked_until"])

    def record_login(self, ip_address=None):
        """Enregistre la dernière connexion réussie."""
        self.last_login_at = timezone.now()
        self.last_login_ip = ip_address
        self.reset_failed_login()


# ─────────────────────────────────────────────
# AUDIT LOG
# ─────────────────────────────────────────────

class ActionChoices(models.TextChoices):
    LOGIN          = "LOGIN",          "Connexion"
    LOGOUT         = "LOGOUT",         "Déconnexion"
    LOGIN_FAILED   = "LOGIN_FAILED",   "Échec de connexion"
    PASSWORD_RESET = "PASSWORD_RESET", "Réinitialisation mot de passe"
    UPDATE_ROLE    = "UPDATE_ROLE",    "Modification du rôle"
    CREATE_USER    = "CREATE_USER",    "Création utilisateur"
    DEACTIVATE     = "DEACTIVATE",     "Désactivation compte"
    VIEW_RESOURCE  = "VIEW_RESOURCE",  "Consultation ressource"
    EXPORT_DATA    = "EXPORT_DATA",    "Export de données"


class StatusChoices(models.TextChoices):
    SUCCESS = "SUCCESS", "Succès"
    FAILURE = "FAILURE", "Échec"


class AuditLog(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,  # conserve les logs même si l'utilisateur est supprimé
        null=True,
        blank=True,
        related_name="audit_logs",
        db_column="user_id"
    )
    action      = models.CharField(max_length=100, choices=ActionChoices.choices)
    resource    = models.CharField(max_length=100, blank=True, null=True)
    resource_id = models.UUIDField(null=True, blank=True)
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    user_agent  = models.TextField(blank=True, null=True)
    status      = models.CharField(max_length=20, choices=StatusChoices.choices)
    detail      = models.JSONField(null=True, blank=True)  # JSONB en PostgreSQL
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        verbose_name = "Journal d'audit"
        verbose_name_plural = "Journal d'audit"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["action"]),
        ]
        # Empêche toute modification — append-only
        # À renforcer au niveau de la BDD avec une règle PostgreSQL

    def __str__(self):
        user_str = str(self.user) if self.user else "utilisateur supprimé"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.action} — {user_str} ({self.status})"

    def save(self, *args, **kwargs):
        """Bloque toute mise à jour — les logs sont immuables."""
        if self.pk:
            raise PermissionError("Les entrées d'audit sont immuables et ne peuvent pas être modifiées.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Bloque toute suppression."""
        raise PermissionError("Les entrées d'audit ne peuvent pas être supprimées.")
