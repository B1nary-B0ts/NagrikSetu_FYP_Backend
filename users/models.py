from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class User(AbstractUser):
    ROLE_CHOICES = [
        ('citizen', 'Citizen'),
        ('dept_head', 'Department Head'),
        ('dept_worker', 'Department Worker'),
        ('municipal_corp_head', 'Municipal Corporation Head'),
        ('ward_head', 'Ward Head'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=10, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    # password_hash = models.TextField()

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return f"{self.name} ({self.role})"


class Citizen(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="citizen_profile"
    )

    def __str__(self):
        return self.user.name
