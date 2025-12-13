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

from django.conf import settings


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)          # e.g. "CSE", "IT"
    full_name = models.CharField(max_length=200)                  # e.g. "Computer Science and Engineering"

    def __str__(self):
        return self.name


class Batch(models.Model):
    """
    One final-year batch, e.g. 2025-2026.
    """
    name = models.CharField(max_length=20, unique=True)           # "2025-2026"
    start_year = models.IntegerField()
    end_year = models.IntegerField()

    def __str__(self):
        return self.name


class ClassSection(models.Model):
    """
    A class inside a department, like CSE-A, CSE-B.
    """
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    name = models.CharField(max_length=20)                        # "CSE-A"

    class Meta:
        unique_together = ("department", "batch", "name")

    def __str__(self):
        return f"{self.name} ({self.batch})"


class FacultyProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=50, unique=True)
    is_hod = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.employee_id}"


class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    roll_number = models.CharField(max_length=50, unique=True)
    semester = models.IntegerField()

    def __str__(self):
        return f"{self.roll_number} - {self.user.get_full_name() or self.user.username}"

class Team(models.Model):
    """
    A project team of exactly 4 students.
    """
    name = models.CharField(max_length=100)  # e.g. "Team Phoenix"
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE)

    team_leader = models.OneToOneField(
        StudentProfile,
        related_name="leading_team",
        on_delete=models.PROTECT,
    )

    members = models.ManyToManyField(
        StudentProfile,
        related_name="teams",
        blank=True,
    )

    mentor = models.ForeignKey(
        FacultyProfile,
        related_name="mentored_teams",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    coordinator = models.ForeignKey(
        FacultyProfile,
        related_name="coordinated_teams",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    is_approved = models.BooleanField(default=False)   # proposal approved
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.department.name} - {self.batch})"
    
class ProjectProposal(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REVISION = "REVISION", "Revision required"
        REJECTED = "REJECTED", "Rejected"

    # one proposal per team
    team = models.OneToOneField(
        Team,
        on_delete=models.CASCADE,
        related_name="proposal",
    )

    # core fields filled by TL
    title = models.CharField(max_length=200)
    problem_statement = models.TextField()
    objectives = models.TextField(blank=True)
    domain = models.CharField(max_length=200, blank=True)  # domain / technology
    expected_outcomes = models.TextField(blank=True)
    estimated_duration_weeks = models.IntegerField(null=True, blank=True)

    preferred_mentor = models.ForeignKey(
        FacultyProfile,
        related_name="preferred_projects",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    coordinator_comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.team.name} - {self.title}"
    
def proposal_upload_path(instance, filename):
    # stored as: proposals/<team_name>/<timestamp>_<filename>
    import time
    safe_team = instance.proposal.team.name.replace(" ", "_")
    return f"proposals/{safe_team}/{int(time.time())}_{filename}"

class ProposalDocument(models.Model):
    proposal = models.ForeignKey(
        ProjectProposal,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    file = models.FileField(upload_to=proposal_upload_path)
    uploaded_by = models.ForeignKey(
        StudentProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.proposal.team.name} - {self.file.name}"



class Invitation(models.Model):
    """
    TL invites students; they accept/reject.
    """
    from_student = models.ForeignKey(
        StudentProfile,
        related_name="sent_invitations",
        on_delete=models.CASCADE,
    )
    to_student = models.ForeignKey(
        StudentProfile,
        related_name="received_invitations",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("REJECTED", "Rejected"),
        ("EXPIRED", "Expired"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")

    def __str__(self):
        return f"Invite {self.from_student} -> {self.to_student} ({self.status})"

