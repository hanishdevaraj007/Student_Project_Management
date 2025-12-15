from django.urls import path
from . import views,staff_views
app_name="core"
urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_redirect, name="dashboard_redirect"),
    path("student/dashboard/", views.student_dashboard, name="student_dashboard"),
    path("faculty/dashboard/", views.faculty_dashboard, name="faculty_dashboard"),
    path("hod/dashboard/", staff_views.hod_dashboard, name="hod_dashboard"),
    path('coordinator/proposals/', staff_views.coordinator_proposal_list, name='coordinator_proposals'),
    path('coordinator/proposals/<int:proposal_id>/', staff_views.coordinator_proposal_detail, name='coordinator_proposal_detail'),
        # HOD views
    path(
        "hod/proposals/",
        staff_views.hod_proposal_list,
        name="hod_proposal_list",
    ),

    path(
        "hod/proposals/<int:proposal_id>/",
        staff_views.hod_proposal_detail,
        name="hod_proposal_detail",
    ),
    path("mentor/dashboard/", staff_views.mentor_dashboard, name="mentor_dashboard"),
    path("advisor/dashboard/", staff_views.advisor_dashboard, name="advisor_dashboard"),
    path("hod/faculty/", staff_views.hod_faculty_list, name="hod_faculty_list"),

        # Coordinator review management
    path(
        "coordinator/team/<int:team_id>/reviews/",
        staff_views.coordinator_team_reviews,
        name="coordinator_team_reviews",
    ),
    path(
        "coordinator/team/<int:team_id>/reviews/<str:review_type>/",
        staff_views.coordinator_edit_review,
        name="coordinator_edit_review",
    ),

]
