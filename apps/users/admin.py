from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils import timezone
from .models import User, Role, Permission, AuditLog


# ─────────────────────────────────────────────
# ROLE
# ─────────────────────────────────────────────

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display    = ("name", "description", "user_count")
    search_fields   = ("name",)
    ordering        = ("name",)

    def user_count(self, obj):
        return obj.users.filter(deleted_at__isnull=True).count()
    user_count.short_description = "Utilisateurs actifs"


# ─────────────────────────────────────────────
# PERMISSION
# ─────────────────────────────────────────────

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display  = ("role", "resource", "read", "write", "update", "delete", "download")
    list_filter   = ("read", "write", "update", "delete", "download")
    search_fields = ("role__name", "resource")


# ─────────────────────────────────────────────
# USER
# ─────────────────────────────────────────────

@admin.register(User)
class CustomUserAdmin(UserAdmin):

    # ── Colonnes affichées dans la liste ──────
    list_display = (
        "email",           # remplace "username"
        "full_name",
        "role",
        "is_active",
        "two_factor_enabled",
        "account_status",
        "created_at",
    )

    list_filter  = ("is_active", "is_staff", "two_factor_enabled", "role", "gender")
    search_fields = ("email", "first_name", "last_name", "phone_number_primal")
    ordering      = ("email",)          # remplace "username"

    # ── Champs en lecture seule ───────────────
    readonly_fields = (
        "usid",
        "created_at",
        "updated_at",       # remplace "date_joined"
        "last_login_at",
        "last_login_ip",
        "failed_login_attempts",
        "locked_until",
        "deleted_at",
    )

    # ── Formulaire de détail (fieldsets) ──────
    fieldsets = (
        ("Identité", {
            "fields": ("usid", "email", "first_name", "last_name", "gender",
                       "phone_number_primal", "phone_number_second")
        }),
        ("Rôle & accès", {
            "fields": ("role", "is_active", "is_staff", "is_superuser")
        }),
        ("Double authentification", {
            "classes": ("collapse",),
            "fields": ("two_factor_enabled", "two_factor_secret")
        }),
        ("Sécurité", {
            "classes": ("collapse",),
            "fields": ("failed_login_attempts", "locked_until",
                       "password_reset_token", "password_reset_expires")
        }),
        ("Traçabilité", {
            "classes": ("collapse",),
            "fields": ("last_login_at", "last_login_ip",
                       "created_at", "updated_at", "deleted_at",
                       "email_verified_at")
        }),
    )

    # ── Formulaire de création ─────────────────
    add_fieldsets = (
        ("Créer un utilisateur", {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "gender",
                       "phone_number_primal", "role",
                       "password1", "password2", "is_active", "is_staff"),
        }),
    )

    # ── Colonnes calculées ────────────────────

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = "Nom complet"
    full_name.admin_order_field = "last_name"

    def account_status(self, obj):
        if obj.deleted_at:
            return format_html('<span style="color:#dc2626;">Supprimé</span>')
        if obj.is_locked:
            return format_html('<span style="color:#d97706;">Verrouillé</span>')
        if not obj.is_active:
            return format_html('<span style="color:#6b7280;">Inactif</span>')
        return format_html('<span style="color:#16a34a;">Actif</span>')
    account_status.short_description = "Statut"

    # ── Actions personnalisées ─────────────────

    @admin.action(description="Désactiver les comptes sélectionnés")
    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Déverrouiller les comptes sélectionnés")
    def unlock_users(self, request, queryset):
        queryset.update(failed_login_attempts=0, locked_until=None)

    actions = ["deactivate_users", "unlock_users"]


# ─────────────────────────────────────────────
# AUDIT LOG
# ─────────────────────────────────────────────

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ("created_at", "user", "action", "resource", "status", "ip_address")
    list_filter   = ("action", "status")
    search_fields = ("user__email", "resource", "ip_address")
    ordering      = ("-created_at",)
    readonly_fields = (
        "id", "user", "action", "resource", "resource_id",
        "ip_address", "user_agent", "status", "detail", "created_at"
    )

    # Empêche toute création ou modification depuis l'admin
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False