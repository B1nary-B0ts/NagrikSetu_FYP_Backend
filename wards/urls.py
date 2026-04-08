# geo/urls.py
from django.urls import path
from .views import (
    WardDashboardOverviewView,
    CriticalHighIssuesView,
    EscalatedIssuesView,
    WorkerPerformanceView,
    DepartmentLoadView,
    GeographicHotspotView,
    DepartmentHeadOverviewView,
    ResolutionTimeTrendsView,
)

urlpatterns = [
    # Auth
    # path("ward-head/login/",  WardHeadLoginView.as_view(),  name="ward-head-login"),
    # path("ward-head/logout/", WardHeadLogoutView.as_view(), name="ward-head-logout"),

    # Dashboard
    path("ward-head/dashboard/overview/",         WardDashboardOverviewView.as_view()),
    path("ward-head/dashboard/critical-issues/",  CriticalHighIssuesView.as_view()),
    path("ward-head/dashboard/escalated/",        EscalatedIssuesView.as_view()),
    path("ward-head/dashboard/worker-performance/", WorkerPerformanceView.as_view()),
    path("ward-head/dashboard/department-load/",  DepartmentLoadView.as_view()),
    path("ward-head/dashboard/hotspots/",         GeographicHotspotView.as_view()),
    path("ward-head/dashboard/dept-heads/",       DepartmentHeadOverviewView.as_view()),
    path("ward-head/dashboard/resolution-trends/", ResolutionTimeTrendsView.as_view()),
]