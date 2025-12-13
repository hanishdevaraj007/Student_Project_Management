from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class UserType(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        FACULTY = "FACULTY", "Faculty"
        HOD = "HOD", "Head of Department"

    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.STUDENT,
    )

    # later we can add more fields like phone, etc.

    def __str__(self):
        return f"{self.username} ({self.user_type})"
