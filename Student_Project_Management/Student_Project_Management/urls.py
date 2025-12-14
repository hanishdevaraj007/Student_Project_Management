"""
URL configuration for Student_Project_Management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from core import views as core_views
from core import views as core_views
from core import staff_views



urlpatterns = [
    path("admin/", admin.site.urls),
    path("", core_views.login_view, name="login"),
    path("logout/", core_views.logout_view, name="logout"),
    path("home/", core_views.dashboard_redirect, name="dashboard_redirect"),
    path("student/dashboard/", core_views.student_dashboard, name="student_dashboard"),
    path("faculty/dashboard/", core_views.faculty_dashboard, name="faculty_dashboard"),
    path("hod/dashboard/", core_views.hod_dashboard, name="hod_dashboard"),
    path("student/invite/send/", core_views.send_invite, name="send_invite"),
    path(
        "student/invite/respond/<int:invite_id>/<str:action>/",
        core_views.respond_invite,
        name="respond_invite",
    ),
    path("student/team/create/", core_views.create_team_view, name="create_team"),
    path("student/proposal/", core_views.proposal_view, name="proposal"),
        # Coordinator views
    path(
        "coordinator/proposals/",
        staff_views.coordinator_proposal_list,
        name="coordinator_proposals",
    ),
    path(
        "coordinator/proposals/<int:proposal_id>/",
        staff_views.coordinator_proposal_detail,
        name="coordinator_proposal_detail",
    ),
    path(
        "hod/proposals/",
        staff_views.hod_proposal_list,
        name="hod_proposals_list",
    ),
    path(
        "hod/proposals/<int:proposal_id>/",
        staff_views.hod_proposal_detail,
        name="hod_proposal_detail",
    ),
    path("mentor/dashboard/", staff_views.mentor_dashboard, name="mentor_dashboard"),
    path("advisor/dashboard/", staff_views.advisor_dashboard, name="advisor_dashboard"),

]
