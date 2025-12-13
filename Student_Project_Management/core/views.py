from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import User, StudentProfile, Invitation, Team, ProjectProposal
from django.db import models


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
    student = StudentProfile.objects.select_related(
        "department", "class_section", "batch", "user"
    ).get(user=request.user)

        # is this student already in any team? (as leader or member)
    is_leader = Team.objects.filter(team_leader=student).exists()
    is_member = Team.objects.filter(members=student).exists()
    already_in_team = is_leader or is_member
        # find team where this student is leader or member
    team = None
    if already_in_team:
        team = Team.objects.filter(team_leader=student).first()
        if team is None:
            team = Team.objects.filter(members=student).first()


    # invitations received by this student
    received_invites = Invitation.objects.filter(
        to_student=student
    ).order_by("-created_at")

    # invitations sent by this student
    sent_invites = Invitation.objects.filter(
        from_student=student
    ).order_by("-created_at")

    # count of invitations this student has accepted
        # invitations sent by this student that were accepted
    accepted_invites_count = Invitation.objects.filter(
        from_student=student,
        status="ACCEPTED",
    ).count()

    accepted_invites = Invitation.objects.filter(
        from_student=student,
        status="ACCEPTED",
    ).select_related("to_student", "to_student__user")

    if request.method == "POST":
        team_name = request.POST.get("team_name", "").strip()
        member_ids = request.POST.getlist("member_ids")

        if not team_name:
            messages.error(request, "Team name is required.")
            return redirect("create_team")

        if len(member_ids) != 3:
            messages.error(request, "You must select exactly 3 members.")
            return redirect("create_team")

        # load selected members
        members = StudentProfile.objects.filter(id__in=member_ids)

        if members.count() != 3:
            messages.error(request, "Some selected students were not found.")
            return redirect("create_team")

        # safety: ensure none of them is already in another team
        conflict = Team.objects.filter(
            models.Q(team_leader__in=members) | models.Q(members__in=members)
        ).exists()
        if conflict:
            messages.error(request, "One of the selected members is already in another team.")
            return redirect("create_team")

        # create team
        team = Team.objects.create(
            name=team_name,
            team_leader=student,
            department=student.department,
            batch=student.batch,
            class_section=student.class_section,
        )
        team.members.set(list(members) + [student])  # include leader as member too
        team.save()

        messages.success(request, "Team created successfully.")
        return redirect("student_dashboard")



    # temporary flag: later we will also check team membership here
    can_create_team = (accepted_invites_count >= 3) and (not already_in_team)

    context = {
        "student": student,
        "invitations": received_invites,
        "sent_invitations": sent_invites,
        "accepted_invites_count": accepted_invites_count,
        "can_create_team": can_create_team,
        "already_in_team":already_in_team,
        "team":team,
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

    student = StudentProfile.objects.get(user=user)

    if request.method == "POST":
        roll = request.POST.get("roll_number")

        try:
            target = StudentProfile.objects.get(
                roll_number=roll,
                department=student.department,
                batch=student.batch,
            )
        except StudentProfile.DoesNotExist:
            messages.error(request, "Student with that roll was not found in your batch.")
            return redirect("student_dashboard")

        if target == student:
            messages.error(request, "You cannot invite yourself.")
            return redirect("student_dashboard")

        pending_count = Invitation.objects.filter(
            to_student=target,
            status="PENDING",
        ).count()
        if pending_count >= 5:
            messages.error(request, "This student already has 5 pending invitations.")
            return redirect("student_dashboard")

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

        if not title or not problem:
            messages.error(request, "Title and problem statement are required.")
            return redirect("proposal")

        proposal.title = title
        proposal.problem_statement = problem
        proposal.status = ProjectProposal.Status.PENDING
        proposal.save()

        messages.success(request, "Proposal saved.")
        return redirect("proposal")

    context = {
        "team": team,
        "proposal": proposal,
        "is_leader": is_leader,
    }
    return render(request, "dashboards/proposal.html", context)
