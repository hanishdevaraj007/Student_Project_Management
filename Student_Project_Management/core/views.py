from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db import models
from .models import (
    User,
    StudentProfile,
    Invitation,
    Team,
    ProjectProposal,
    ProposalDocument,
)
from django.conf import settings

def can_be_teammates(s1: StudentProfile, s2: StudentProfile) -> bool:
    """
    Students can be teammates only if:
    - Same department
    - Same batch
    - And either same section OR cross-section is allowed by settings
    """
    if s1.department_id != s2.department_id:
        return False
    if s1.batch_id != s2.batch_id:
        return False

    allow_cross_section = getattr(settings, "ALLOW_CROSS_SECTION_TEAMS", True)
    if allow_cross_section:
        return True
    return s1.class_section_id == s2.class_section_id




def home(request):
    return redirect(reverse(":login"))

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard_redirect")
    return render(request, "auth/login.html")



@login_required
def logout_view(request):
    logout(request)
    return redirect(reverse("login"))


@login_required
def dashboard_redirect(request):
    user: User = request.user
    if user.user_type == User.UserType.STUDENT:
        return redirect(reverse("student_dashboard"))
    if user.user_type == User.UserType.HOD:
        return redirect(reverse("hod_dashboard"))
    # default: faculty
    return redirect(reverse("faculty_dashboard"))


@login_required
def student_dashboard(request):
    user: User = request.user

    if user.user_type != User.UserType.STUDENT:
        return redirect("dashboard_redirect")

    # get this student's profile
    try:
        student = StudentProfile.objects.select_related(
            "department", "batch", "class_section", "user"
        ).get(user=user)
    except StudentProfile.DoesNotExist:
        return redirect("dashboard_redirect")

    # find a team where this student is leader or member
    team = None
    is_leader = Team.objects.filter(team_leader=student).exists()
    is_member = Team.objects.filter(members=student).exists()
    already_in_team = is_leader or is_member

    first_review = second_review = final_review = None
    if team:
        first_review = team.reviews.filter(review_type=Review.Type.FIRST).first()
        second_review = team.reviews.filter(review_type=Review.Type.SECOND).first()
        final_review = team.reviews.filter(review_type=Review.Type.FINAL).first()


    if already_in_team:
        team = Team.objects.select_related(
            "department", "batch", "class_section", "proposal"
        ).prefetch_related(
            "members",
            "reviews",
            "proposal__documents",
        ).filter(
            models.Q(team_leader=student) | models.Q(members=student)
        ).distinct().first()

    # invitations received by this student
    received_invitations = Invitation.objects.filter(
        to_student=student
    ).order_by("-created_at")

    # invitations sent by this student
    sent_invitations = Invitation.objects.filter(
        from_student=student
    ).order_by("-created_at")

    context = {
        "student": student,
        "team": team,
        "already_in_team": already_in_team,
        "received_invitations": received_invitations,
        "sent_invitations": sent_invitations,
        "first_review": first_review,
        "second_review": second_review,
        "final_review": final_review,
    }
    return render(request, "dashboards/student_dashboard.html", context)



@login_required
def faculty_dashboard(request):
    user: User = request.user
    if user.user_type == User.UserType.FACULTY:
        return render(request, "dashboards/faculty_dashboard.html")
    else:
        return redirect(reverse("dashboard_redirect"))

@login_required
def hod_dashboard(request):
    user: User = request.user
    if user.user_type == User.UserType.HOD:
        return render(request, "dashboards/hod_dashboard.html")
    else:
        return redirect(reverse("dashboard_redirect"))
    
@login_required
def send_invite(request):
    user: User = request.user
    if user.user_type != User.UserType.STUDENT:
        return redirect("dashboard_redirect")

    student = StudentProfile.objects.select_related(
        "department", "batch", "class_section"
    ).get(user=user)

    if request.method == "POST":
        roll = (request.POST.get("roll_number") or "").strip().upper()

        try:
            # Look up by roll only; department/batch/section will be checked by can_be_teammates
            target = StudentProfile.objects.select_related(
                "department", "batch", "class_section"
            ).get(roll_number=roll)
        except StudentProfile.DoesNotExist:
            messages.error(request, "Student with that roll number does not exist.")
            return redirect("student_dashboard")

        # Cannot invite yourself
        if target == student:
            messages.error(request, "You cannot invite yourself.")
            return redirect("student_dashboard")

        # Enforce department+batch and optional section rule
        if not can_be_teammates(student, target):
            messages.error(
                request,
                "You can invite only students in your department and batch "
                "(section rule depends on department policy).",
            )
            return redirect("student_dashboard")

        # Limit pending invitations *to that target*
        pending_count = Invitation.objects.filter(
            to_student=target,
            status="PENDING",
        ).count()
        if pending_count >= 5:
            messages.error(request, "This student already has 5 pending invitations.")
            return redirect("student_dashboard")

        # Avoid duplicate pending invite from same student to same target
        existing = Invitation.objects.filter(
            from_student=student,
            to_student=target,
            status="PENDING",
        ).exists()
        if existing:
            messages.info(request, "You already sent an invitation to this student.")
            return redirect("student_dashboard")

        Invitation.objects.create(
            from_student=student,
            to_student=target,
        )
        messages.success(request, "Invitation sent.")
        return redirect("student_dashboard")

    return redirect("student_dashboard")

@login_required
def respond_invite(request, invite_id, action):
    user: User = request.user
    if user.user_type != User.UserType.STUDENT:
        return redirect("dashboard_redirect")

    student = StudentProfile.objects.get(user=user)
    invite = get_object_or_404(
        Invitation,
        id=invite_id,
        to_student=student,
    )

    if invite.status != "PENDING":
        messages.info(request, "This invitation is already processed.")
        return redirect("student_dashboard")

    if action == "accept":
        Invitation.objects.filter(
            to_student=student,
            status="PENDING",
        ).exclude(id=invite.id).update(status="EXPIRED")
        invite.status = "ACCEPTED"
        invite.save()
        messages.success(request, "Invitation accepted.")
    elif action == "reject":
        invite.status = "REJECTED"
        invite.save()
        messages.info(request, "Invitation rejected.")

    return redirect("student_dashboard")

@login_required
def create_team_view(request):
    user: User = request.user
    if user.user_type != User.UserType.STUDENT:
        return redirect("dashboard_redirect")

    student = StudentProfile.objects.get(user=user)

    # same checks as dashboard
    is_leader = Team.objects.filter(team_leader=student).exists()
    is_member = Team.objects.filter(members=student).exists()
    already_in_team = is_leader or is_member

    accepted_invites_count = Invitation.objects.filter(
        from_student=student,
        status="ACCEPTED",
    ).count()

    accepted_invites = Invitation.objects.filter(
        from_student=student,
        status="ACCEPTED",
    ).select_related("to_student", "to_student__user")


    can_create_team = (accepted_invites_count >= 3) and (not already_in_team)

    if not can_create_team:
        messages.error(request, "You are not allowed to create a team.")
        return redirect("student_dashboard")
    
    # NEW: handle form submit
    if request.method == "POST":
        team_name = request.POST.get("team_name", "").strip()
        member_ids = request.POST.getlist("member_ids")

        if not team_name:
            messages.error(request, "Team name is required.")
            return redirect("create_team")

        if len(member_ids) < 2 or len(member_ids) > 3:
            messages.error(request, "You must select 2 or 3 members.")
            return redirect("create_team")

        members = StudentProfile.objects.filter(id__in=member_ids)
        if members.count() != len(member_ids):
            messages.error(request, "Some selected students were not found.")
            return redirect("create_team")


        conflict = Team.objects.filter(
            models.Q(team_leader__in=members) | models.Q(members__in=members)
        ).exists()
        if conflict:
            messages.error(request, "One of the selected members is already in another team.")
            return redirect("create_team")

        team = Team.objects.create(
            name=team_name,
            team_leader=student,
            department=student.department,
            batch=student.batch,
            class_section=student.class_section,
        )
        # include leader plus 3 members
        team.members.set(list(members) + [student])
        team.save()

        messages.success(request, "Team created successfully.")
        return redirect("student_dashboard")


    # TEMP: simple placeholder
    return render(request, "dashboards/create_team.html", {
        "student": student,
        "accepted_invites_count": accepted_invites_count,
        "accepted_invites":accepted_invites,
    })

@login_required
def proposal_view(request):
    user: User = request.user
    if user.user_type != User.UserType.STUDENT:
        return redirect("dashboard_redirect")

    student = StudentProfile.objects.get(user=user)

    # must be in a team
    team = Team.objects.filter(team_leader=student).first()
    if team is None:
        team = Team.objects.filter(members=student).first()

    if team is None:
        messages.error(request, "You must be in a team to submit a proposal.")
        return redirect("student_dashboard")

    # only TL can edit; members can only view
    is_leader = (team.team_leader_id == student.id)

    proposal, created = ProjectProposal.objects.get_or_create(team=team)

    if request.method == "POST":
        if not is_leader:
            messages.error(request, "Only the team leader can edit the proposal.")
            return redirect("proposal")

        title = request.POST.get("title", "").strip()
        problem = request.POST.get("problem_statement", "").strip()
        objectives = request.POST.get("objectives", "").strip()
        domain = request.POST.get("domain", "").strip()
        expected = request.POST.get("expected_outcomes", "").strip()
        duration_raw = request.POST.get("estimated_duration_weeks", "").strip()

        if not title or not problem:
            messages.error(request, "Title and problem statement are required.")
            return redirect("proposal")

        # parse duration (optional)
        duration = None
        if duration_raw:
            try:
                duration = int(duration_raw)
            except ValueError:
                messages.error(request, "Estimated duration must be a number.")
                return redirect("proposal")

        proposal.title = title
        proposal.problem_statement = problem
        proposal.objectives = objectives
        proposal.domain = domain
        proposal.expected_outcomes = expected
        proposal.estimated_duration_weeks = duration
        proposal.status = ProjectProposal.Status.PENDING
        proposal.save()

        pdf_file = request.FILES.get("proposal_pdf")
        if pdf_file:
            ProposalDocument.objects.create(
                proposal=proposal,
                file=pdf_file,
                uploaded_by=student,
            )



        messages.success(request, "Proposal saved.")
        return redirect("proposal")

    context = {
        "team": team,
        "proposal": proposal,
        "is_leader": is_leader,
    }
    return render(request, "dashboards/proposal.html", context)
