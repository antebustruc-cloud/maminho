from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model. Role determines what the account can do in Maminho:

    - admin: infinite KC, organizes competitions, runs the medical center economy.
    - club_owner: owns exactly one Club (Phase 1 assumption), manages facilities/squad.
    - manager: owns a ManagerProfile, scouts/claims free agents, negotiates club deals.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        CLUB_OWNER = "club_owner", "Club owner"
        MANAGER = "manager", "Manager"

    role = models.CharField(max_length=20, choices=Role.choices)

    def __str__(self):
        return f"{self.username} ({self.role})"
