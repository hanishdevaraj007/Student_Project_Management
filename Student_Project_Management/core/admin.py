from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Department, Batch, ClassSection, FacultyProfile, StudentProfile
from .models import User,Team, Invitation, ProjectProposal, ProposalDocument


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # show user_type in the list
    list_display = ("username", "email", "first_name", "last_name", "user_type", "is_staff")
    list_filter = ("user_type", "is_staff", "is_superuser", "is_active")

    fieldsets = UserAdmin.fieldsets + (
        ("Role information", {"fields": ("user_type",)}),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "full_name")
    search_fields = ("name", "full_name")


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ("name", "start_year", "end_year")


@admin.register(ClassSection)
class ClassSectionAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "batch")
    list_filter = ("department", "batch")


@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "employee_id", "department", "is_hod")
    list_filter = ("department", "is_hod")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "roll_number", "department", "class_section", "batch", "semester")
    list_filter = ("department", "class_section", "batch", "semester")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "class_section", "batch", "team_leader", "mentor", "coordinator", "is_approved")
    list_filter = ("department", "class_section", "batch", "is_approved")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("from_student", "to_student", "status", "created_at")
    list_filter = ("status",)


@admin.register(ProjectProposal)
class ProjectProposalAdmin(admin.ModelAdmin):
    list_display = ("title", "team", "status", "preferred_mentor", "created_at")
    list_filter = ("status", "team__department","team__batch")
    search_filter = ("title","team__name")

@admin.register(ProposalDocument)
class ProposalDocumentAdmin(admin.ModelAdmin):
    list_display = ("proposal", "file", "uploaded_by", "uploaded_at")
    list_filter = ("uploaded_at",)

