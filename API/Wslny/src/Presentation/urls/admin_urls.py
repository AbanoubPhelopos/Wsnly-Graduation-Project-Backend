from django.urls import path
from src.Presentation.views.admin_views import (
    ChangeUserRoleView,
    UserListView,
    RouteAnalyticsOverviewView,
    RouteAnalyticsTopRoutesView,
)

urlpatterns = [
    path("admin/change-role", ChangeUserRoleView.as_view(), name="change-role"),
    path("admin/users", UserListView.as_view(), name="list-users"),
    path(
        "admin/analytics/routes/overview",
        RouteAnalyticsOverviewView.as_view(),
        name="routes-analytics-overview",
    ),
    path(
        "admin/analytics/routes/top-routes",
        RouteAnalyticsTopRoutesView.as_view(),
        name="routes-analytics-top-routes",
    ),
]
