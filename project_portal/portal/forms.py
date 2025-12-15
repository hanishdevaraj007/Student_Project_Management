from django import forms
from django.contrib.auth.models import User
from .models import Team, StudentProfile, FacultyProfile, Review, PanelEvaluation, ReviewFile
from django.core.exceptions import ValidationError

class StudentLoginForm(forms.Form):
    roll_number = forms.CharField(max_length=20, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter Roll Number'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter Password'
    }))


class FacultyLoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter Username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter Password'
    }))


class TeamForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        queryset=StudentProfile.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    class Meta:
        model = Team
        fields = ['name', 'members']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, department=None, batch=None, class_section=None, **kwargs):
        super().__init__(*args, **kwargs)
        if department and batch and class_section:
            self.fields['members'].queryset = StudentProfile.objects.filter(
                department=department,
                batch=batch,
                class_section=class_section
            ).exclude(teams__isnull=False)
        
        # Validate max 4 members
    
    def clean_members(self):
        members = self.cleaned_data.get('members')
        if members and len(members) > 4:
            raise ValidationError("Team cannot have more than 4 members.")
        if members and len(members) < 3:
            raise ValidationError("Team must have at least 3 members.")
        return members


class ReviewSetupForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['date_time', 'grace_days', 'evaluator1', 'evaluator2']
        widgets = {
            'date_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'grace_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 2}),
            'evaluator1': forms.Select(attrs={'class': 'form-select'}),
            'evaluator2': forms.Select(attrs={'class': 'form-select'}),
        }


class PanelEvaluationForm(forms.ModelForm):
    class Meta:
        model = PanelEvaluation
        fields = ['score', 'comment']
        widgets = {
            'score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ReviewFileForm(forms.ModelForm):
    class Meta:
        model = ReviewFile
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }


class ReviewFreezeForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter reason for freeze/unfreeze'
        }),
        required=False
    )
