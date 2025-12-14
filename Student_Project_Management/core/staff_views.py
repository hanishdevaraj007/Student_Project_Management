from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q, Case, When, Value, IntegerField
from core import staff_views
from .models import (
    User,
    FacultyProfile,
    ProjectProposal,
    ProposalDocument,
)


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
def mentor_dashboard(request):
    user: User = request.user

    if user.user_type != User.UserType.FACULTY:
        return redirect("dashboard_redirect")

    try:
        faculty = FacultyProfile.objects.get(user=user)
    except FacultyProfile.DoesNotExist:
        return redirect("dashboard_redirect")

    # Teams where this faculty is mentor
    from .models import Team  # if not imported yet
    teams = Team.objects.select_related(
        "department", "batch", "class_section", "proposal"
    ).filter(mentor=faculty)

    context = {
        "faculty": faculty,
        "teams": teams,
    }
    return render(request, "dashboards/mentor_dashboard.html", context)

@login_required
def advisor_dashboard(request):
    user: User = request.user

    if user.user_type != User.UserType.FACULTY:
        return redirect("dashboard_redirect")

    try:
        faculty = FacultyProfile.objects.get(user=user)
    except FacultyProfile.DoesNotExist:
        return redirect("dashboard_redirect")

    if not faculty.is_advisor:
        return redirect("dashboard_redirect")

    from .models import StudentProfile, Team

    students = StudentProfile.objects.select_related(
        "user", "department", "batch", "class_section"
    ).filter(department=faculty.department)

    # Optional: prefetch team & proposal
    from django.db.models import Prefetch
    teams = Team.objects.select_related("proposal").prefetch_related("members")
    students = students.prefetch_related(
        Prefetch("team_set", queryset=teams, to_attr="prefetched_teams")
    )

    context = {
        "faculty": faculty,
        "students": students,
    }
    return render(request, "dashboards/advisor_dashboard.html", context)
