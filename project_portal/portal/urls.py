from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),
    
    # Dashboards
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('faculty/dashboard/', views.faculty_dashboard, name='faculty_dashboard'),
    path('hod/dashboard/', views.hod_dashboard, name='hod_dashboard'),
    path('coordinator/dashboard/', views.coordinator_dashboard, name='coordinator_dashboard'),
    path('supervisor/dashboard/', views.supervisor_dashboard, name='supervisor_dashboard'),
    path('evaluator/dashboard/', views.evaluator_dashboard, name='evaluator_dashboard'),
    path('advisor/dashboard/', views.advisor_dashboard, name='advisor_dashboard'),
    path('principal/dashboard/', views.principal_dashboard, name='principal_dashboard'),
    
    # Teams
    path('team/create/', views.create_team, name='create_team'),
    
    # Reviews
    path('review/<int:review_id>/detail/', views.review_detail, name='review_detail'),
    path('review/<int:review_id>/edit/', views.review_edit_sheet, name='review_edit_sheet'),
    path('review/<int:review_id>/files/', views.review_files, name='review_files'),
]
