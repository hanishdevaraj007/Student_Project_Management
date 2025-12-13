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
]
