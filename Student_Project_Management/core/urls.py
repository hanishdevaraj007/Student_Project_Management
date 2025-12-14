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

]
