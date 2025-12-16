from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404

from .models import (
    Department,
    Batch,
    ClassSection,
    FacultyProfile,
    StudentProfile,
    Team,
    ProjectProposal,
    Review,
    ReviewRubric,
    ReviewMark,
    Invitation,
)

User = get_user_model()


# -----------------------
# Helper functions
# -----------------------


def _get_faculty(user):
    """Return FacultyProfile for this user or None."""
    try:
        return FacultyProfile.objects.select_related("department").get(user=user)
    except FacultyProfile.DoesNotExist:
        return None


def _require_hod(user):
    faculty = _get_faculty(user)
    return faculty if faculty and faculty.is_hod else None


def _require_coordinator(user):
    faculty = _get_faculty(user)
    return faculty if faculty and faculty.is_coordinator else None


def _require_coordinator_or_hod(user):
    faculty = _get_faculty(user)
    if faculty and (faculty.is_coordinator or faculty.is_hod):
        return faculty
    return None


# -----------------------
# HOD views
# -----------------------


@login_required
def hod_dashboard(request):
    user = request.user
    faculty = _require_hod(user)
    if not faculty:
        messages.error(request, "You are not marked as HOD.")
        return redirect("faculty_dashboard")

    # Teams and reviews in this department
    teams = (
        Team.objects.filter(department=faculty.department)
        .select_related("department", "batch", "class_section")
        .prefetch_related("members")
    )
    reviews = Review.objects.filter(team__department=faculty.department).select_related(
        "team"
    )

    context = {
        "faculty": faculty,
        "total_teams": teams.count(),
        "total_reviews": reviews.count(),
        "teams": teams,
        "reviews": reviews.order_by("date"),
    }
    return render(request, "dashboards/hod_dashboard.html", context)


@login_required
def hod_proposal_list(request):
    user = request.user
    faculty = _require_hod(user)
    if not faculty:
        messages.error(request, "You are not marked as HOD.")
        return redirect("faculty_dashboard")

    proposals = (
        ProjectProposal.objects.filter(team__department=faculty.department)
        .select_related("team", "team__class_section", "team__batch")
        .order_by("created_at")
    )

    context = {
        "faculty": faculty,
        "proposals": proposals,
    }
    return render(request, "hod_proposals.html", context)


@login_required
def hod_proposal_detail(request, proposal_id):
    user = request.user
    faculty = _require_hod(user)
    if not faculty:
        messages.error(request, "You are not marked as HOD.")
        return redirect("faculty_dashboard")

    proposal = get_object_or_404(
        ProjectProposal.objects.select_related(
            "team", "team__department", "team__batch", "team__class_section"
        ).prefetch_related("team__members", "documents"),
        id=proposal_id,
    )

    if proposal.team.department != faculty.department:
        messages.error(request, "This proposal is not in your department.")
        return redirect("hod_proposal_list")

    context = {
        "faculty": faculty,
        "proposal": proposal,
    }
    return render(request, "hod_proposals.html", context)


@login_required
def hod_faculty_list(request):
    user = request.user
    faculty = _require_hod(user)
    if not faculty:
        messages.error(request, "You are not marked as HOD.")
        return redirect("faculty_dashboard")

    staff = FacultyProfile.objects.filter(department=faculty.department).select_related(
        "user"
    )

    context = {
        "faculty": faculty,
        "staff_list": staff,
    }
    return render(request, "hod_faculty_list.html", context)


# -----------------------
# Coordinator views
# -----------------------


@login_required
def coordinator_dashboard(request):
    user = request.user
    faculty = _require_coordinator(user)
    if not faculty:
        messages.error(request, "You are not marked as coordinator.")
        return redirect("faculty_dashboard")

    teams = (
        Team.objects.filter(department=faculty.department)
        .select_related("department", "batch", "class_section")
        .prefetch_related("members", "proposal")
    )
    reviews = Review.objects.filter(team__department=faculty.department).select_related(
        "team"
    )

    context = {
        "faculty": faculty,
        "total_teams": teams.count(),
        "total_reviews": reviews.count(),
        "teams": teams.order_by("name"),
        "reviews": reviews.order_by("date"),
    }
    return render(request, "dashboards/coordinator_dashboard.html", context)


@login_required
def coordinator_proposal_list(request):
    user = request.user
    faculty = _require_coordinator(user)
    if not faculty:
        messages.error(request, "You are not marked as coordinator.")
        return redirect("faculty_dashboard")

    proposals = (
        ProjectProposal.objects.filter(team__department=faculty.department)
        .select_related("team", "team__class_section", "team__batch")
        .order_by("created_at")
    )

    context = {
        "faculty": faculty,
        "proposals": proposals,
    }
    return render(request, "coordinator_proposals.html", context)


@login_required
def coordinator_proposal_detail(request, proposal_id):
    user = request.user
    faculty = _require_coordinator(user)
    if not faculty:
        messages.error(request, "You are not marked as coordinator.")
        return redirect("faculty_dashboard")

    proposal = get_object_or_404(
        ProjectProposal.objects.select_related(
            "team", "team__department", "team__batch", "team__class_section"
        ).prefetch_related("team__members", "documents"),
        id=proposal_id,
    )

    if proposal.team.department != faculty.department:
        messages.error(request, "This proposal is not in your department.")
        return redirect("coordinator_proposals")

    context = {
        "faculty": faculty,
        "proposal": proposal,
    }
    return render(request, "coordinator_proposal_detail.html", context)


@login_required
def coordinator_team_reviews(request, team_id):
    user = request.user
    faculty = _require_coordinator(user)
    if not faculty:
        messages.error(request, "You are not marked as coordinator.")
        return redirect("faculty_dashboard")

    team = get_object_or_404(
        Team.objects.select_related(
            "department", "batch", "class_section"
        ).prefetch_related("members"),
        id=team_id,
    )
    if team.department != faculty.department:
        messages.error(request, "This team is not in your department.")
        return redirect("coordinator_dashboard")

    reviews = Review.objects.filter(team=team).order_by("date")

    context = {
        "faculty": faculty,
        "team": team,
        "reviews": reviews,
    }
    return render(request, "reviews/coordinator_team_review.html", context)


@login_required
def coordinator_edit_review(request, team_id, review_id):
    user = request.user
    faculty = _require_coordinator(user)
    if not faculty:
        messages.error(request, "You are not marked as coordinator.")
        return redirect("faculty_dashboard")

    team = get_object_or_404(Team, id=team_id)
    review = get_object_or_404(Review, id=review_id, team=team)

    if team.department != faculty.department:
        messages.error(request, "This review is not in your department.")
        return redirect("coordinator_dashboard")

    if request.method == "POST":
        # Minimal editing: update date and requirements
        date_str = request.POST.get("date", "")
        requirements = request.POST.get("requirements", "")
        if date_str:
            try:
                review.date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Invalid date format.")
        review.requirements = requirements
        review.save()
        messages.success(request, "Review updated.")
        return redirect("coordinator_team_reviews", team_id=team.id)

    context = {
        "faculty": faculty,
        "team": team,
        "review": review,
    }
    return render(request, "reviews/coordinator_edit_review.html", context)


# -----------------------
# Advisor views
# -----------------------


@login_required
def advisor_dashboard(request):
    user = request.user
    faculty = _get_faculty(user)
    if not faculty or not faculty.is_advisor:
        messages.error(request, "You are not marked as advisor.")
        return redirect("faculty_dashboard")

    # If you later add advisor_class_section in FacultyProfile, filter by that.
    # For now, list all students in advisor's department.
    students = (
        StudentProfile.objects.filter(department=faculty.department)
        .select_related("user", "class_section", "batch")
        .order_by("class_section__name", "roll_number")
    )

    # Map each student to team/proposal summary
    team_map = {
        member.id: member.teams.select_related("department").first()
        for member in students
    }

    context = {
        "faculty": faculty,
        "students": students,
        "team_map": team_map,
    }
    return render(request, "dashboards/advisor_dashboard.html", context)


# -----------------------
# Supervisor / Mentor views
# -----------------------


@login_required
def supervisor_dashboard(request):
    """
    Supervisor (mentor) dashboard: shows teams where this faculty is mentor.
    """
    user = request.user
    faculty = _get_faculty(user)
    if not faculty:
        messages.error(request, "Faculty profile not found.")
        return redirect("faculty_dashboard")

    teams = (
        Team.objects.select_related(
            "department", "batch", "class_section", "proposal"
        )
        .prefetch_related("proposal__documents", "members")
        .filter(mentor=faculty)
    )

    context = {
        "faculty": faculty,
        "teams": teams,
    }
    return render(request, "dashboards/supervisor_dashboard.html", context)


# Optional alias if you still use mentor_dashboard anywhere:
mentor_dashboard = supervisor_dashboard


# -----------------------
# Evaluator views
# -----------------------


@login_required
def evaluator_dashboard(request):
    """
    Dashboard for evaluators: list of reviews where this faculty is in the panel.
    """
    user = request.user
    faculty = _get_faculty(user)
    if not faculty:
        messages.error(request, "Faculty profile not found.")
        return redirect("faculty_dashboard")

    reviews = (
        Review.objects.filter(panel_members=faculty)
        .select_related("team", "team__department", "team__batch", "team__class_section")
        .order_by("date")
    )

    context = {
        "faculty": faculty,
        "reviews": reviews,
    }
    return render(request, "dashboards/evaluator_dashboard.html", context)


# -----------------------
# Principal view
# -----------------------


@login_required
def principal_dashboard(request):
    user = request.user
    # Simplest rule: principal = superuser
    if not user.is_superuser:
        messages.error(request, "You are not principal.")
        return redirect("dashboard_redirect")

    total_teams = Team.objects.count()
    total_reviews = Review.objects.count()

    teams = (
        Team.objects.select_related("department", "batch", "class_section", "mentor")
        .prefetch_related("members")
        .order_by("department__name", "name")
    )

    context = {
        "user": user,
        "total_teams": total_teams,
        "total_reviews": total_reviews,
        "teams": teams,
    }
    return render(request, "dashboards/principal_dashboard.html", context)


# -----------------------
# Team detail (shared)
# -----------------------


@login_required
def team_detail(request, team_id):
    """
    Common team detail page visible to:
    - Team members
    - Team mentor/supervisor
    - HOD / coordinator of that department
    - Principal
    """
    user = request.user

    team = get_object_or_404(
        Team.objects.select_related(
            "department", "batch", "class_section", "mentor"
        ).prefetch_related("members", "proposal__documents", "reviews"),
        id=team_id,
    )

    can_view = False

    # Student member of team
    try:
        student = StudentProfile.objects.get(user=user)
        if team.members.filter(id=student.id).exists():
            can_view = True
    except StudentProfile.DoesNotExist:
        student = None

    # Faculty roles
    faculty = _get_faculty(user)
    if faculty:
        if faculty == team.mentor:
            can_view = True
        if faculty.is_hod and faculty.department == team.department:
            can_view = True
        if faculty.is_coordinator and faculty.department == team.department:
            can_view = True

    # Principal can view everything
    if user.is_superuser:
        can_view = True

    if not can_view:
        messages.error(request, "You are not allowed to view this team.")
        return redirect("dashboard_redirect")

    proposal = getattr(team, "proposal", None)
    reviews = team.reviews.all().order_by("date")

    context = {
        "team": team,
        "proposal": proposal,
        "reviews": reviews,
    }
    return render(request, "teams/team_detail.html", context)
