from django.urls import path

from src.Presentation.views.orchestrator import RouteOrchestratorView


urlpatterns = [
    path("route", RouteOrchestratorView.as_view(), name="route-orchestrator"),
]
