from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q, Case, When, Value, IntegerField,Prefetch
from core import staff_views
from .models import (
    User,
    FacultyProfile,
    ProjectProposal,
    ProposalDocument,
    StudentProfile,
    Team,
    Review,
    ReviewRubric,
)
import datetime
from django.utils import timezone



def _require_coordinator(user: User):
    """
    Helper: return (faculty_profile, error_response)
    error_response is None when user is a valid coordinator.
    """
    if user.user_type != User.UserType.FACULTY:
        return None, redirect("dashboard_redirect")

    try:
        faculty = FacultyProfile.objects.get(user=user)
    except FacultyProfile.DoesNotExist:
        return None, redirect("dashboard_redirect")

    if not getattr(faculty, "is_coordinator", False):
        return None, redirect("dashboard_redirect")

    return faculty, None


@login_required
def coordinator_proposal_list(request):
    """
    Coordinator dashboard: list proposals for their department/batch.
    """
    user: User = request.user
    faculty, error_response = _require_coordinator(user)
    if error_response:
        return error_response

    # base queryset: proposals from coordinator's department and batch
    qs = ProjectProposal.objects.select_related(
        "team",
        "team__department",
        "team__batch",
        "team__class_section",
    ).filter(
        team__department=faculty.department,
    )

    # Optional filtering by status from query string ?status=PENDING
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)

    # Optional search by team name or title
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            models.Q(team__name__icontains=q) |
            models.Q(title__icontains=q)
        )

    proposals = qs.annotate(
    status_order=Case(
        When(status=ProjectProposal.Status.PENDING, then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
    )
    ).order_by("status_order", "-updated_at")


    context = {
        "faculty": faculty,
        "proposals": proposals,
        "selected_status": status or "",
        "search_query": q,
        "status_choices": ProjectProposal.Status.choices,
    }
    return render(request, "dashboards/coordinator_proposals.html", context)


@login_required
def coordinator_proposal_detail(request, proposal_id):
    """
    Coordinator view for a single proposal:
    - sees all fields and uploaded PDFs
    - can set status + comment
    """
    user: User = request.user
    faculty, error_response = _require_coordinator(user)
    if error_response:
        return error_response
    possible_mentors = FacultyProfile.objects.filter(
    department=faculty.department
    ).exclude(id=faculty.id)

    proposal = get_object_or_404(
        ProjectProposal.objects.select_related(
            "team",
            "team__department",
            "team__batch",
            "team__class_section",
        ),
        id=proposal_id,
        team__department=faculty.department,
       
    )

    if request.method == "POST":
        new_status = request.POST.get("status")
        comment = request.POST.get("coordinator_comment", "").strip()
        mentor_id = request.POST.get("mentor_id")

        # basic validation: status must be one of the known choices
        valid_statuses = {choice[0] for choice in ProjectProposal.Status.choices}
        if new_status not in valid_statuses:
            messages.error(request, "Invalid status selected.")
            return redirect("coordinator_proposal_detail", proposal_id=proposal.id)

        proposal.status = new_status
        proposal.coordinator_comment = comment
        proposal.save()

        # Assign mentor only if APPROVED and mentor selected
        if new_status == ProjectProposal.Status.APPROVED and mentor_id:
            try:
                mentor = FacultyProfile.objects.get(id=mentor_id, department=faculty.department)
                proposal.team.mentor = mentor
                proposal.team.save()
            except FacultyProfile.DoesNotExist:
                messages.error(request, "Selected mentor is invalid.")

        messages.success(request, "Proposal status updated.")
        return redirect("coordinator_proposal_detail", proposal_id=proposal.id)

    documents = proposal.documents.all().order_by("-uploaded_at")

    context = {
        "faculty": faculty,
        "proposal": proposal,
        "documents": documents,
        "status_choices": ProjectProposal.Status.choices,
        "possible_mentors": possible_mentors,
    }
    return render(request, "dashboards/coordinator_proposal_detail.html", context)

def require_coordinator_or_hod(user: User):
    """
    Return (faculty_profile, error_response).
    Allows either:
      - Faculty with is_coordinator=True, or
      - Faculty with is_hod=True.
    """
    if user.user_type != User.UserType.FACULTY and user.user_type != User.UserType.HOD:
        return None, redirect("dashboardredirect")

    try:
        faculty = FacultyProfile.objects.get(user=user)
    except FacultyProfile.DoesNotExist:
        return None, redirect("dashboardredirect")

    if getattr(faculty, "is_coordinator", False) or getattr(faculty, "is_hod", False):
        return faculty, None

    return None, redirect("dashboardredirect")


@login_required
def coordinator_team_reviews(request, team_id):
    """Coordinator/HOD see all reviews (1st/2nd/final) for a team."""
    user: User = request.user
    faculty, error_response = require_coordinator_or_hod(user)
    if error_response:
        return error_response

    team = get_object_or_404(
        Team.objects.select_related("department", "batch", "class_section"),
        id=team_id,
        department=faculty.department,
    )

    reviews = team.reviews.all().order_by("date")

    context = {
        "faculty": faculty,
        "team": team,
        "reviews": reviews,
    }
    return render(request, "dashboards/coordinator_team_reviews.html", context)

@login_required
def coordinator_edit_review(request, team_id, review_type):
    user: User = request.user
    faculty, error_response = require_coordinator_or_hod(user)
    if error_response:
        return error_response

    team = get_object_or_404(
        Team.objects.select_related("department"),
        id=team_id,
        department=faculty.department,
    )

    # Try to fetch existing review; do NOT create yet
    try:
        review = Review.objects.get(team=team, review_type=review_type)
    except Review.DoesNotExist:
        review = None

    panel_candidates = FacultyProfile.objects.filter(
        department=faculty.department
    ).select_related("user")

    if request.method == "POST":
        # create or update on POST
        if review is None:
            review = Review(team=team, review_type=review_type, created_by=faculty)

        date_str = request.POST.get("date")
        requirements = request.POST.get("requirements", "").strip()
        panel_ids = request.POST.getlist("panel_members")

        if date_str:
            try:
                review.date = datetime.date.fromisoformat(date_str)
            except Exception:
                messages.error(request, "Invalid date.")
                return redirect("coordinator_edit_review", team_id=team.id, review_type=review_type)
        else:
            review.date = None  # or keep previous date

        review.requirements = requirements
        review.created_by = faculty
        review.save()

        review.panel_members.set(
            FacultyProfile.objects.filter(
                id__in=panel_ids,
                department=faculty.department,
            )
        )

        review.rubrics.all().delete()
        names = request.POST.getlist("rubric_name")
        weights = request.POST.getlist("rubric_weight")
        max_scores = request.POST.getlist("rubric_max_score")

        for name, weight, max_score in zip(names, weights, max_scores):
            name = name.strip()
            if not name:
                continue
            ReviewRubric.objects.create(
                review=review,
                name=name,
                weight=int(weight or 0),
                max_score=int(max_score or 10),
            )

        messages.success(request, "Review details saved.")
        return redirect("coordinator_team_reviews", team_id=team.id)

    context = {
        "faculty": faculty,
        "team": team,
        "review": review,
        "panel_candidates": panel_candidates,
        "review_type": review_type,
    }
    return render(request, "dashboards/coordinator_edit_review.html", context)


def require_hod_user(user): 
    """Helper: return faculty_profile, error_response (error_response is None when user is a valid HOD)."""
    if user.user_type != User.UserType.HOD:
        return None, redirect('dashboard_redirect')
    try:
        faculty = FacultyProfile.objects.get(user=user)
    except FacultyProfile.DoesNotExist:
        return None, redirect('dashboard_redirect')
    if not getattr(faculty, 'is_hod', False):
        return None, redirect('dashboard_redirect')
    return faculty, None

@login_required
def hod_dashboard(request):
    """HOD dashboard: overview of ALL proposals across their department (no batch filter)."""
    user = User(request.user)
    faculty, error_response = require_hod_user(user)
    if error_response:
        return error_response
    
    # Base queryset: ALL proposals in HOD's department (no batch restriction)
    qs = ProjectProposal.objects.select_related(
        'team', 'team__department', 'team__batch', 'team__class_section',
    ).filter(
        team__department=faculty.department
    )
    
    # Optional filtering by status (?status=PENDING)
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    
    # Optional search by team name or title (?q=teamname)
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(team__name__icontains=q) | Q(title__icontains=q)
        )
    
    # Order: PENDING first, then by recency
    proposals = qs.annotate(
        status_order=Case(
            When(status=ProjectProposal.Status.PENDING, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by('status_order', '-updated_at')
    
    context = {
        'faculty': faculty,
        'proposals': proposals,
        'selected_status': status or '',
        'search_query': q,
        'status_choices': ProjectProposal.Status.choices,
    }
    return render(request, 'dashboards/hod_dashboard.html', context)

@login_required
def hod_proposal_list(request):
    """
    HOD dashboard: list all proposals in their department.
    """
    user: User = request.user
    faculty, error_response = require_hod_user(user)
    if error_response:
        return error_response

    qs = ProjectProposal.objects.select_related(
        "team",
        "team__department",
        "team__batch",
        "team__class_section",
    ).filter(
        team__department=faculty.department,
    )

    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)

    batch_id = request.GET.get("batch")
    if batch_id:
        qs = qs.filter(team__batch_id=batch_id)

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            models.Q(team__name__icontains=q) |
            models.Q(title__icontains=q)
        )

    proposals = qs.annotate(
        status_order=Case(
            When(status=ProjectProposal.Status.PENDING, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by("status_order", "-updated_at")

    # distinct batches in this department for filter dropdown
    batches = qs.values_list("team__batch_id", "team__batch__name").distinct()

    context = {
        "faculty": faculty,
        "proposals": proposals,
        "selected_status": status or "",
        "selected_batch": int(batch_id) if batch_id else None,
        "search_query": q,
        "status_choices": ProjectProposal.Status.choices,
        "batches": batches,
    }
    return render(request, "dashboards/hod_proposals.html", context)


@login_required
def hod_proposal_detail(request, proposal_id):
    """
    HOD view for a single proposal (read-only, reuses coordinator detail template).
    """
    user: User = request.user
    faculty, error_response = require_hod_user(user)
    if error_response:
        return error_response

    proposal = get_object_or_404(
        ProjectProposal.objects.select_related(
            "team",
            "team__department",
            "team__batch",
            "team__class_section",
        ),
        id=proposal_id,
        team__department=faculty.department,
    )

    documents = proposal.documents.all().order_by("-uploaded_at")

    context = {
        "faculty": faculty,
        "proposal": proposal,
        "documents": documents,
        "status_choices": ProjectProposal.Status.choices,
        "is_hod_readonly": True,
    }
    return render(request, "dashboards/coordinator_proposal_detail.html", context)

@login_required
def hod_faculty_list(request):
    """
    HOD view: manage coordinators in their department.
    """
    user: User = request.user
    faculty, error_response = require_hod_user(user)
    if error_response:
        return error_response

    department = faculty.department

    if request.method == "POST":
        # list of faculty ids that should be coordinators
        ids = request.POST.getlist("coordinator_ids")
        ids = [int(i) for i in ids]

        FacultyProfile.objects.filter(department=department).update(is_coordinator=False)
        FacultyProfile.objects.filter(id__in=ids, department=department).update(
            is_coordinator=True
        )

        messages.success(request, "Coordinator assignments updated.")

    faculty_list = FacultyProfile.objects.select_related("user").filter(
        department=department
    ).order_by("user__username")

    context = {
        "faculty": faculty,
        "faculty_list": faculty_list,
    }
    return render(request, "dashboards/hod_faculty_list.html", context)


@login_required
def advisor_dashboard(request):
    """
    Advisor dashboard: all students in advisor's department + their team/project.
    """
    user: User = request.user

    if user.user_type != User.UserType.FACULTY:
        return redirect("dashboard_redirect")

    try:
        faculty = FacultyProfile.objects.get(user=user)
    except FacultyProfile.DoesNotExist:
        return redirect("dashboard_redirect")

    if not getattr(faculty, "is_advisor", False):
        return redirect("dashboard_redirect")

    students = StudentProfile.objects.select_related(
        "user", "department", "batch", "class_section"
    ).filter(department=faculty.department)

    teams = Team.objects.select_related(
        "department",
        "batch",
        "class_section",
        "proposal",
    ).prefetch_related(
        "proposal__documents",
        "reviews",
    ).filter(mentor=faculty)


    context = {
        "faculty": faculty,
        "students": students,
    }
    return render(request, "dashboards/advisor_dashboard.html", context)


@login_required
def advisor_dashboard(request):
    user: User = request.user

    if user.user_type != User.UserType.FACULTY:
        return redirect("dashboard_redirect")

    try:
        faculty = FacultyProfile.objects.get(user=user)
    except FacultyProfile.DoesNotExist:
        return redirect("dashboard_redirect")

    if not getattr(faculty, "is_advisor", False):
        return redirect("dashboard_redirect")

    students = StudentProfile.objects.select_related(
    "user", "department", "batch", "class_section"
    ).filter(
    department=faculty.department
    ).order_by(
    "class_section__name",
    "teams__name",
    "user__username",
    )

    context = {
        "faculty": faculty,
        "students": students,
    }
    return render(request, "dashboards/advisor_dashboard.html", context)

@login_required
def mentor_dashboard(request):
    """
    Mentor dashboard: shows teams where this faculty is mentor.
    """
    user: User = request.user

    if user.user_type != User.UserType.FACULTY:
        return redirect("dashboard_redirect")

    try:
        faculty = FacultyProfile.objects.get(user=user)
    except FacultyProfile.DoesNotExist:
        return redirect("dashboard_redirect")

    teams = Team.objects.select_related(
        "department",
        "batch",
        "class_section",
        "proposal",
    ).prefetch_related(
    "proposal__documents",
    ).filter(mentor=faculty)

    context = {
        "faculty": faculty,
        "teams": teams,
    }
    return render(request, "dashboards/mentor_dashboard.html", context)
