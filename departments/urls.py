from django.urls import path
from .views import DeptHeadIssuesView

urlpatterns = [
    path('issues/', DeptHeadIssuesView.as_view(), name='dept_head_issues'),
]