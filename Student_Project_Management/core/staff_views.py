from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q, Case, When, Value, IntegerField

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

        # basic validation: status must be one of the known choices
        valid_statuses = {choice[0] for choice in ProjectProposal.Status.choices}
        if new_status not in valid_statuses:
            messages.error(request, "Invalid status selected.")
            return redirect("coordinator_proposal_detail", proposal_id=proposal.id)

        proposal.status = new_status
        proposal.coordinator_comment = comment
        proposal.save()

        messages.success(request, "Proposal status updated.")
        return redirect("coordinator_proposal_detail", proposal_id=proposal.id)

    documents = proposal.documents.all().order_by("-uploaded_at")

    context = {
        "faculty": faculty,
        "proposal": proposal,
        "documents": documents,
        "status_choices": ProjectProposal.Status.choices,
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
