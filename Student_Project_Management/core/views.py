from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse

from .models import User

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard_redirect")  # no change here
    return render(request, "auth/login.html")



@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard_redirect(request):
    user: User = request.user
    if user.user_type == User.UserType.STUDENT:
        return redirect("student_dashboard")
    if user.user_type == User.UserType.HOD:
        return redirect("hod_dashboard")
    # default: faculty
    return redirect("faculty_dashboard")


@login_required
def student_dashboard(request):
    return render(request, "dashboards/student_dashboard.html")


@login_required
def faculty_dashboard(request):
    return render(request, "dashboards/faculty_dashboard.html")


@login_required
def hod_dashboard(request):
    return render(request, "dashboards/hod_dashboard.html")
