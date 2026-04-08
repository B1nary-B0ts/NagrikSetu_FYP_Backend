from django.urls import path
from .views import (
    CorpDashboardOverviewView,
    WardComparisonView,
    CorpCriticalHighIssuesView,
    CorpEscalatedIssuesView,
    CorpIssueCategoryFrequencyView,
    CorpGeographicHotspotView,
    CorpDepartmentPerformanceView,
    CorpWorkerPerformanceView,
)

urlpatterns = [
    path("corp-head/dashboard/overview/",            CorpDashboardOverviewView.as_view()),
    path("corp-head/dashboard/ward-comparison/",     WardComparisonView.as_view()),
    path("corp-head/dashboard/critical-issues/",     CorpCriticalHighIssuesView.as_view()),
    path("corp-head/dashboard/escalated/",           CorpEscalatedIssuesView.as_view()),
    path("corp-head/dashboard/issue-frequency/",     CorpIssueCategoryFrequencyView.as_view()),
    path("corp-head/dashboard/hotspots/",            CorpGeographicHotspotView.as_view()),
    path("corp-head/dashboard/dept-performance/",    CorpDepartmentPerformanceView.as_view()),
    path("corp-head/dashboard/worker-performance/",  CorpWorkerPerformanceView.as_view()),
]