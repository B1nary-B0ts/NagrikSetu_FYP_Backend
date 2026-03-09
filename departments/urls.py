from django.urls import path
from .views import DeptHeadIssuesView, AvailableWorkersView, AssignWorkersView

urlpatterns = [
    path('issues/', DeptHeadIssuesView.as_view(), name='dept_head_issues'),
    path('workers/available/', AvailableWorkersView.as_view(), name='available_workers'),
    path('issues/<int:issue_id>/assign-workers/', AssignWorkersView.as_view(), name='assign_workers'),
]