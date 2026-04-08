# geo/urls.py
from django.urls import path
from .views import ResolveLocationView, WardBoundaryView, CorpBoundaryView


urlpatterns = [
    path("resolve-location/", ResolveLocationView.as_view(), name="resolve-location"),
    path("ward/boundary/",  WardBoundaryView.as_view(),  name="ward-boundary"),
    path("corp/boundary/",  CorpBoundaryView.as_view(),  name="corp-boundary"),
]
