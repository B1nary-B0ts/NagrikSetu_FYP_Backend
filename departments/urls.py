from django.urls import path
from .views import DeptHeadIssuesView, AvailableWorkersView, AssignWorkersView, ResolveIssueView, WorkerIssuesView

urlpatterns = [
    path('issues/', DeptHeadIssuesView.as_view(), name='dept_head_issues'),
    path('workers/available/', AvailableWorkersView.as_view(), name='available_workers'),
    path('issues/<int:issue_id>/assign-workers/', AssignWorkersView.as_view(), name='assign_workers'),
    path('worker/my-issues/', WorkerIssuesView.as_view(), name='worker_issues'),
    path('worker/issues/<int:issue_id>/resolve/', ResolveIssueView.as_view(), name='resolve_issue'),
]