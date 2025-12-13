from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from .models import User, StudentProfile, Invitation


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

    # invitations received by this student
    received_invites = Invitation.objects.filter(
        to_student=student
    ).order_by("-created_at")

    # invitations sent by this student
    sent_invites = Invitation.objects.filter(
        from_student=student
    ).order_by("-created_at")

    context = {
        "student": student,
        "invitations": received_invites,
        "sent_invitations": sent_invites,
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
