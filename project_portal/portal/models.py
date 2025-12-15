from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from datetime import datetime, timedelta

# ========== Core Models ==========

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Batch(models.Model):
    name = models.CharField(max_length=50)
    year = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.year})"

    class Meta:
        ordering = ['-year']


class ClassSection(models.Model):
    name = models.CharField(max_length=50)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.department.name} ({self.batch.year})"

    class Meta:
        unique_together = ('name', 'department', 'batch')
        ordering = ['name']


# ========== User Profiles ==========

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    roll_number = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True)
    class_section = models.ForeignKey(ClassSection, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.roll_number})"

    class Meta:
        ordering = ['roll_number']


class FacultyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='faculty_profile')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    
    # Role flags
    is_hod = models.BooleanField(default=False)
    is_portal_coordinator = models.BooleanField(default=False)
    is_supervisor = models.BooleanField(default=False)
    is_evaluator = models.BooleanField(default=False)
    is_advisor = models.BooleanField(default=False)
    is_principal = models.BooleanField(default=False)
    
    freeze_count = models.IntegerField(default=0)
    unfreeze_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()}"

    class Meta:
        ordering = ['user__username']


# ========== Teams & Proposals ==========

class Team(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE)
    members = models.ManyToManyField(StudentProfile, related_name='teams')
    supervisor = models.ForeignKey(FacultyProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='supervised_teams')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_member_count(self):
        return self.members.count()

    class Meta:
        unique_together = ('name', 'batch', 'class_section')
        ordering = ['name']


class ProjectProposal(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    team = models.OneToOneField(Team, on_delete=models.CASCADE, related_name='proposal')
    title = models.CharField(max_length=200)
    abstract = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.team.name}"

    class Meta:
        ordering = ['-updated_at']


class ProposalDocument(models.Model):
    proposal = models.ForeignKey(ProjectProposal, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='proposals/')
    version = models.IntegerField(default=1)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.proposal.title} - v{self.version}"

    class Meta:
        ordering = ['-version']


# ========== Reviews & Rubrics ==========

class Review(models.Model):
    REVIEW_TYPE_CHOICES = [
        ('zeroth', 'Zeroth'),
        ('first', 'Review 1'),
        ('second', 'Review 2'),
    ]
    
    FREEZE_STATE_CHOICES = [
        ('not_frozen', 'Not Frozen'),
        ('frozen_soft', 'Soft Frozen'),
        ('hard_locked', 'Hard Locked'),
    ]
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='reviews')
    review_type = models.CharField(max_length=20, choices=REVIEW_TYPE_CHOICES)
    date_time = models.DateTimeField(null=True, blank=True)
    grace_days = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(2)])
    evaluator1 = models.ForeignKey(FacultyProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='evaluator1_reviews')
    evaluator2 = models.ForeignKey(FacultyProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='evaluator2_reviews')
    hod_freeze_state = models.CharField(max_length=20, choices=FREEZE_STATE_CHOICES, default='not_frozen')
    first_freeze_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.team.name} - {self.get_review_type_display()}"

    def is_editable(self):
        """Check if marks can be edited now"""
        if self.hod_freeze_state != 'not_frozen':
            return False
        if not self.date_time:
            return False
        today = datetime.now().date()
        review_date = self.date_time.date()
        grace_until = review_date + timedelta(days=self.grace_days)
        return review_date <= today <= grace_until

    class Meta:
        unique_together = ('team', 'review_type')
        ordering = ['team', 'review_type']


class ManagementWindow(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    review_type = models.CharField(max_length=20, choices=Review.REVIEW_TYPE_CHOICES)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.department.name} - {self.review_type} ({self.batch.year})"

    class Meta:
        unique_together = ('department', 'batch', 'review_type')


class RubricTemplate(models.Model):
    name = models.CharField(max_length=100)
    review_type = models.CharField(max_length=20, choices=Review.REVIEW_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.review_type})"

    class Meta:
        unique_together = ('name', 'review_type')


class RubricItem(models.Model):
    template = models.ForeignKey(RubricTemplate, on_delete=models.CASCADE, related_name='items')
    order = models.IntegerField()
    title = models.CharField(max_length=200)
    max_score = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.template.name} - {self.title}"

    class Meta:
        ordering = ['order']
        unique_together = ('template', 'order')


# ========== Marks & History ==========

class PanelEvaluation(models.Model):
    ROLE_CHOICES = [
        ('hod', 'HoD'),
        ('supervisor', 'Supervisor'),
        ('evaluator1', 'Evaluator 1'),
        ('evaluator2', 'Evaluator 2'),
    ]
    
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='evaluations')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    rubric_item = models.ForeignKey(RubricItem, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    score = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    comment = models.TextField(blank=True)
    version_group_id = models.CharField(max_length=50, default='v1')
    version_number = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.review.team.name} - {self.student.user.get_full_name()} - {self.rubric_item.title}"

    class Meta:
        ordering = ['review', 'student', 'rubric_item']
        unique_together = ('review', 'student', 'rubric_item', 'role', 'version_number')


class FreezeHistory(models.Model):
    ACTION_CHOICES = [
        ('freeze', 'Freeze'),
        ('unfreeze', 'Unfreeze'),
    ]
    
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='freeze_history')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    by = models.ForeignKey(FacultyProfile, on_delete=models.SET_NULL, null=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.review.team.name} - {self.action} at {self.created_at}"

    class Meta:
        ordering = ['-created_at']


class ReviewFile(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='reviews/')
    version = models.IntegerField(default=1)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.review.team.name} - {self.review.review_type} - v{self.version}"

    class Meta:
        ordering = ['-version']


# ========== Date Change History ==========

class DateChangeHistory(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='date_changes')
    old_date = models.DateTimeField(null=True, blank=True)
    new_date = models.DateTimeField(null=True, blank=True)
    changed_by = models.ForeignKey(FacultyProfile, on_delete=models.SET_NULL, null=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.review.team.name} - date changed at {self.created_at}"

    class Meta:
        ordering = ['-created_at']
