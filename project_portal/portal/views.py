from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import (
    StudentProfile, FacultyProfile, Team, Review, RubricTemplate, RubricItem, 
    PanelEvaluation, FreezeHistory, ReviewFile, ProjectProposal, Department, Batch, ClassSection
)
from .forms import (
    StudentLoginForm, FacultyLoginForm, TeamForm, ReviewSetupForm, 
    PanelEvaluationForm, ReviewFileForm, ReviewFreezeForm
)
from datetime import datetime, timedelta



def login_view(request):
    """Combined login for students and faculty/admin."""
    login_type = request.GET.get('type', 'faculty')  # default tab

    if request.method == 'POST':
        login_type = request.POST.get('login_type', 'faculty')

        # ---------- Student login ----------
        if login_type == 'student':
            form = StudentLoginForm(request.POST)
            if form.is_valid():
                roll_number = form.cleaned_data['roll_number']
                password = form.cleaned_data['password']

                try:
                    student = StudentProfile.objects.get(roll_number=roll_number)
                except StudentProfile.DoesNotExist:
                    messages.error(request, 'Invalid roll number or password.')
                    return render(request, 'auth/login.html', {
                        'form': form,
                        'login_type': 'student',
                    })

                user = authenticate(username=student.user.username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('student_dashboard')
                else:
                    messages.error(request, 'Invalid roll number or password.')
                    return render(request, 'auth/login.html', {
                        'form': form,
                        'login_type': 'student',
                    })

        # ---------- Faculty/Admin login ----------
        else:
            form = FacultyLoginForm(request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']

                user = authenticate(username=username, password=password)
                if user is not None:
                    login(request, user)

                    # redirect based on faculty roles
                    try:
                        faculty = user.faculty_profile
                        if faculty.is_principal:
                            return redirect('principal_dashboard')
                        elif faculty.is_hod:
                            return redirect('hod_dashboard')
                        elif faculty.is_portal_coordinator:
                            return redirect('coordinator_dashboard')
                        else:
                            return redirect('faculty_dashboard')
                    except FacultyProfile.DoesNotExist:
                        return redirect('faculty_dashboard')
                else:
                    messages.error(request, 'Invalid username or password.')
                    return render(request, 'auth/login.html', {
                        'form': form,
                        'login_type': 'faculty',
                    })

    # ---------- GET request: show forms ----------
    if login_type == 'student':
        form = StudentLoginForm()
    else:
        form = FacultyLoginForm()

    return render(request, 'auth/login.html', {
        'form': form,
        'login_type': login_type,
    })



def logout_view(request):
    """Logout view"""
    logout(request)
    return redirect('login')


# ========== Student Dashboard ==========

@login_required
def student_dashboard(request):
    """Student dashboard view"""
    try:
        student = request.user.student_profile
    except StudentProfile.DoesNotExist:
        return redirect('login')
    
    team = student.teams.first()
    proposal = ProjectProposal.objects.filter(team=team).first() if team else None
    reviews = Review.objects.filter(team=team) if team else []
    
    context = {
        'student': student,
        'team': team,
        'proposal': proposal,
        'reviews': reviews,
    }
    return render(request, 'dashboards/student_dashboard.html', context)


# ========== Faculty Dashboard ==========

@login_required
def faculty_dashboard(request):
    """Generic faculty dashboard"""
    try:
        faculty = request.user.faculty_profile
    except FacultyProfile.DoesNotExist:
        return redirect('login')
    
    supervised_teams = Team.objects.filter(supervisor=faculty) if faculty.is_supervisor else []
    evaluations = Review.objects.filter(
        Q(evaluator1=faculty) | Q(evaluator2=faculty)
    ) if faculty.is_evaluator else []
    
    context = {
        'faculty': faculty,
        'supervised_teams': supervised_teams,
        'evaluations': evaluations,
    }
    return render(request, 'dashboards/faculty_dashboard.html', context)


# ========== HOD Dashboard ==========

@login_required
def hod_dashboard(request):
    """HOD dashboard view"""
    try:
        hod = request.user.faculty_profile
        if not hod.is_hod:
            return redirect('faculty_dashboard')
    except FacultyProfile.DoesNotExist:
        return redirect('login')
    
    teams = Team.objects.filter(department=hod.department)
    reviews = Review.objects.filter(team__department=hod.department)
    
    context = {
        'hod': hod,
        'teams': teams,
        'reviews': reviews,
    }
    return render(request, 'dashboards/hod_dashboard.html', context)


# ========== Coordinator Dashboard ==========

@login_required
def coordinator_dashboard(request):
    """Coordinator dashboard view"""
    try:
        coordinator = request.user.faculty_profile
        if not coordinator.is_portal_coordinator:
            return redirect('faculty_dashboard')
    except FacultyProfile.DoesNotExist:
        return redirect('login')
    
    teams = Team.objects.filter(department=coordinator.department)
    
    context = {
        'coordinator': coordinator,
        'teams': teams,
    }
    return render(request, 'dashboards/coordinator_dashboard.html', context)


# ========== Supervisor Dashboard ==========

@login_required
def supervisor_dashboard(request):
    """Supervisor dashboard view"""
    try:
        supervisor = request.user.faculty_profile
        if not supervisor.is_supervisor:
            return redirect('faculty_dashboard')
    except FacultyProfile.DoesNotExist:
        return redirect('login')
    
    teams = Team.objects.filter(supervisor=supervisor)
    
    context = {
        'supervisor': supervisor,
        'teams': teams,
    }
    return render(request, 'dashboards/supervisor_dashboard.html', context)


# ========== Evaluator Dashboard ==========

@login_required
def evaluator_dashboard(request):
    """Evaluator dashboard view"""
    try:
        evaluator = request.user.faculty_profile
        if not evaluator.is_evaluator:
            return redirect('faculty_dashboard')
    except FacultyProfile.DoesNotExist:
        return redirect('login')
    
    evaluations = Review.objects.filter(
        Q(evaluator1=evaluator) | Q(evaluator2=evaluator)
    )
    
    context = {
        'evaluator': evaluator,
        'evaluations': evaluations,
    }
    return render(request, 'dashboards/evaluator_dashboard.html', context)


# ========== Advisor Dashboard ==========

@login_required
def advisor_dashboard(request):
    """Advisor dashboard view"""
    try:
        advisor = request.user.faculty_profile
        if not advisor.is_advisor:
            return redirect('faculty_dashboard')
    except FacultyProfile.DoesNotExist:
        return redirect('login')
    
    # Advisors see students in their class
    # TODO: Implement advisor-student mapping
    
    context = {
        'advisor': advisor,
    }
    return render(request, 'dashboards/advisor_dashboard.html', context)


# ========== Principal Dashboard ==========

@login_required
def principal_dashboard(request):
    """Principal dashboard - read-only overview"""
    try:
        principal = request.user.faculty_profile
        if not principal.is_principal:
            return redirect('faculty_dashboard')
    except FacultyProfile.DoesNotExist:
        return redirect('login')
    
    all_teams = Team.objects.all()
    all_reviews = Review.objects.all()
    all_freeze_history = FreezeHistory.objects.all().order_by('-created_at')[:50]
    
    context = {
        'principal': principal,
        'all_teams': all_teams,
        'all_reviews': all_reviews,
        'all_freeze_history': all_freeze_history,
    }
    return render(request, 'dashboards/principal_dashboard.html', context)


# ========== Team Management ==========

@login_required
def create_team(request):
    """Create or edit team"""
    try:
        student = request.user.student_profile
    except StudentProfile.DoesNotExist:
        return redirect('login')
    
    # Check if student is already in a team
    if student.teams.exists():
        messages.warning(request, 'You are already part of a team.')
        return redirect('student_dashboard')
    
    if request.method == 'POST':
        form = TeamForm(
            request.POST,
            department=student.department,
            batch=student.batch,
            class_section=student.class_section
        )
        if form.is_valid():
            team = form.save(commit=False)
            team.department = student.department
            team.batch = student.batch
            team.class_section = student.class_section
            team.save()
            form.save_m2m()
            messages.success(request, 'Team created successfully!')
            return redirect('student_dashboard')
    else:
        form = TeamForm(
            department=student.department,
            batch=student.batch,
            class_section=student.class_section
        )
    
    context = {
        'form': form,
        'student': student,
    }
    return render(request, 'teams/create_team.html', context)


# ========== Review Management ==========

@login_required
def review_detail(request, review_id):
    """Read-only review detail sheet"""
    review = get_object_or_404(Review, id=review_id)
    evaluations = PanelEvaluation.objects.filter(review=review)
    rubric_items = RubricItem.objects.filter(template__review_type=review.review_type)
    
    context = {
        'review': review,
        'evaluations': evaluations,
        'rubric_items': rubric_items,
    }
    return render(request, 'reviews/review_detail.html', context)


@login_required
def review_edit_sheet(request, review_id):
    """Editable review sheet for evaluators"""
    review = get_object_or_404(Review, id=review_id)
    
    # Check if user is authorized and can edit
    try:
        faculty = request.user.faculty_profile
    except FacultyProfile.DoesNotExist:
        return redirect('login')
    
    if review.hod_freeze_state == 'hard_locked':
        messages.error(request, 'This review is hard locked.')
        return redirect('faculty_dashboard')
    
    if review.hod_freeze_state == 'frozen_soft':
        messages.warning(request, 'This review is currently frozen.')
    
    rubric_items = RubricItem.objects.filter(template__review_type=review.review_type)
    students = review.team.members.all()
    
    if request.method == 'POST':
        # TODO: Implement mark submission logic
        messages.success(request, 'Marks submitted successfully!')
        return redirect('faculty_dashboard')
    
    context = {
        'review': review,
        'rubric_items': rubric_items,
        'students': students,
        'is_editable': review.is_editable(),
    }
    return render(request, 'reviews/review_edit_sheet.html', context)


@login_required
def review_files(request, review_id):
    """Review file uploads and versions"""
    review = get_object_or_404(Review, id=review_id)
    files = ReviewFile.objects.filter(review=review).order_by('-version')
    
    if request.method == 'POST':
        form = ReviewFileForm(request.POST, request.FILES)
        if form.is_valid():
            file_obj = form.save(commit=False)
            file_obj.review = review
            # Get next version number
            latest_version = ReviewFile.objects.filter(review=review).order_by('-version').first()
            file_obj.version = (latest_version.version + 1) if latest_version else 1
            file_obj.save()
            messages.success(request, 'File uploaded successfully!')
            return redirect('review_files', review_id=review.id)
    else:
        form = ReviewFileForm()
    
    context = {
        'review': review,
        'files': files,
        'form': form,
    }
    return render(request, 'reviews/review_files.html', context)


# ========== Dashboard redirect ==========

@login_required
def dashboard(request):
    """Smart redirect to appropriate dashboard"""
    try:
        if hasattr(request.user, 'student_profile'):
            return redirect('student_dashboard')
        elif hasattr(request.user, 'faculty_profile'):
            faculty = request.user.faculty_profile
            if faculty.is_principal:
                return redirect('principal_dashboard')
            elif faculty.is_hod:
                return redirect('hod_dashboard')
            elif faculty.is_portal_coordinator:
                return redirect('coordinator_dashboard')
            else:
                return redirect('faculty_dashboard')
    except:
        pass
    
    return redirect('login')
