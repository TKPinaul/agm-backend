from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        DOCTOR = 'DOCTOR', _('Doctor')
        STAFF = 'STAFF', _('Staff')
        PATIENT = 'PATIENT', _('Patient')

    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Phone number'))
    role = models.CharField(
        max_length=20, 
        choices=Role.choices, 
        default=Role.PATIENT,
        verbose_name=_('Role')
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
