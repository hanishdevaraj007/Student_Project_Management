from django.urls import path
from . import views

app_name = "portal"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Role dashboard redirect
    path("dashboard/", views.dashboard_redirect, name="dashboard_redirect"),

    # Student views
    path("student/dashboard/", views.student_dashboard, name="student_dashboard"),
    path("student/team/create/", views.create_team_view, name="create_team"),
    path("student/invite/send/", views.send_invite, name="send_invite"),
    path(
        "student/invite/<int:invite_id>/<str:action>/",
        views.respond_invite,
        name="respond_invite",
    ),
    path("student/proposal/", views.proposal_view, name="proposal"),

    # Faculty generic dashboard (if logged-in faculty without special role)
    path("faculty/dashboard/", views.faculty_dashboard, name="faculty_dashboard"),

    # Advisor
    path("advisor/dashboard/", staff_views.advisor_dashboard, name="advisor_dashboard"),

    # Mentor / Supervisor (your template is supervisor_dashboard.html)
    path("supervisor/dashboard/", staff_views.supervisor_dashboard, name="supervisor_dashboard"),

    # Evaluator
    path("evaluator/dashboard/", staff_views.evaluator_dashboard, name="evaluator_dashboard"),

    # HOD
    path("hod/dashboard/", staff_views.hod_dashboard, name="hod_dashboard"),
    path("hod/faculty/", staff_views.hod_faculty_list, name="hod_faculty_list"),
    path("hod/proposals/", staff_views.hod_proposal_list, name="hod_proposal_list"),
    path(
        "hod/proposals/<int:team_id>/",
        staff_views.hod_proposal_detail,
        name="hod_proposal_detail",
    ),

    # Coordinator
    path(
        "coordinator/dashboard/",
        staff_views.coordinator_dashboard,
        name="coordinator_dashboard",
    ),
    path(
        "coordinator/proposals/",
        staff_views.coordinator_proposal_list,
        name="coordinator_proposals",
    ),
    path(
        "coordinator/proposals/<int:team_id>/",
        staff_views.coordinator_proposal_detail,
        name="coordinator_proposal_detail",
    ),
    # Review management for coordinator
    path(
        "coordinator/team/<int:team_id>/reviews/",
        staff_views.coordinator_team_reviews,
        name="coordinator_team_reviews",
    ),
    path(
        "coordinator/team/<int:team_id>/reviews/<int:review_id>/",
        staff_views.coordinator_edit_review,
        name="coordinator_edit_review",
    ),

    # Principal
    path("principal/dashboard/", staff_views.principal_dashboard, name="principal_dashboard"),

    # Team detail (common view link from HOD/coordinator/supervisor/etc.)
    path(
        "teams/<int:team_id>/",
        staff_views.team_detail,
        name="team_detail",
    ),
]
