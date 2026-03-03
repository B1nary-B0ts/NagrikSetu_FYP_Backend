from django.urls import path
from .views import ReportIssueView 

urlpatterns = [
    path('report/', ReportIssueView.as_view(), name='report_issue'),
]