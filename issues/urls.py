from django.urls import path
from .views import ReportIssueView, MyIssuesView

urlpatterns = [
    path('report/', ReportIssueView.as_view(), name='report_issue'),
    path('my-issues/', MyIssuesView.as_view(), name='my_issues'),
]