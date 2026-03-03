# geo/urls.py
from django.urls import path
from .views import ResolveLocationView

urlpatterns = [
    path("resolve-location/", ResolveLocationView.as_view(), name="resolve-location"),
]
