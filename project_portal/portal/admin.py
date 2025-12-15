from django.contrib import admin
from .models import (
    Department, Batch, ClassSection, StudentProfile, FacultyProfile, Team, 
    ProjectProposal, ProposalDocument, Review, ManagementWindow, RubricTemplate, 
    RubricItem, PanelEvaluation, FreezeHistory, ReviewFile, DateChangeHistory
)

admin.site.register(Department)
admin.site.register(Batch)
admin.site.register(ClassSection)
admin.site.register(StudentProfile)
admin.site.register(FacultyProfile)
admin.site.register(Team)
admin.site.register(ProjectProposal)
admin.site.register(ProposalDocument)
admin.site.register(Review)
admin.site.register(ManagementWindow)
admin.site.register(RubricTemplate)
admin.site.register(RubricItem)
admin.site.register(PanelEvaluation)
admin.site.register(FreezeHistory)
admin.site.register(ReviewFile)
admin.site.register(DateChangeHistory)
