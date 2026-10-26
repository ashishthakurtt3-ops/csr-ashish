from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_ADMIN = 'ADMIN'
    ROLE_STAFF = 'STAFF'
    ROLE_NGO_MANAGER = 'NGO_MANAGER'
    ROLE_CORPORATE = 'CORPORATE_PARTNER'
    ROLE_VIEWER = 'VIEWER'

    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Super Administrator'),
        (ROLE_STAFF, 'Staff / Data Auditor'),
        (ROLE_NGO_MANAGER, 'NGO Representative'),
        (ROLE_CORPORATE, 'Corporate Partner'),
        (ROLE_VIEWER, 'Standard User / Job Seeker'),
    ]

    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default=ROLE_VIEWER)
    phone = models.CharField(max_length=30, blank=True, null=True)
    organization_name = models.CharField(max_length=255, blank=True, null=True)
    designation = models.CharField(max_length=120, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_admin_or_staff(self):
        return self.is_superuser or self.is_staff or self.role in (self.ROLE_ADMIN, self.ROLE_STAFF)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
