from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from src.Presentation.views.auth_views import (
    ChangePasswordView,
    GoogleLoginView,
    LoginView,
    ProfileView,
    RegisterView,
)
from src.Presentation.views.admin_views import (
    ChangeUserRoleView,
    RouteAnalyticsOverviewView,
    RouteAnalyticsQueryView,
    RouteFilterStatsView,
    RouteAnalyticsTopRoutesView,
    RouteUnresolvedStatsView,
    UserListView,
)
from src.Presentation.views.orchestrator import RouteOrchestratorView
from src.Presentation.views.orchestrator import RouteHistoryView
from src.Presentation.views.orchestrator import RouteSearchView
from src.Presentation.views.orchestrator import RouteSearchConfirmView
from src.Presentation.views.orchestrator import RouteMetadataView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/register", RegisterView.as_view(), name="register"),
    path("api/auth/login", LoginView.as_view(), name="login"),
    path("api/auth/google-login", GoogleLoginView.as_view(), name="google-login"),
    path("api/auth/profile", ProfileView.as_view(), name="profile"),
    path(
        "api/auth/change-password", ChangePasswordView.as_view(), name="change-password"
    ),
    path("api/admin/change-role", ChangeUserRoleView.as_view(), name="change-role"),
    path("api/admin/users", UserListView.as_view(), name="list-users"),
    path(
        "api/admin/analytics/routes/overview",
        RouteAnalyticsOverviewView.as_view(),
        name="routes-analytics-overview",
    ),
    path(
        "api/admin/analytics/routes/top-routes",
        RouteAnalyticsTopRoutesView.as_view(),
        name="routes-analytics-top-routes",
    ),
    path(
        "api/admin/analytics/routes/filters",
        RouteFilterStatsView.as_view(),
        name="routes-analytics-filters",
    ),
    path(
        "api/admin/analytics/routes/unresolved",
        RouteUnresolvedStatsView.as_view(),
        name="routes-analytics-unresolved",
    ),
    path(
        "api/admin/analytics/routes/query",
        RouteAnalyticsQueryView.as_view(),
        name="routes-analytics-query",
    ),
    path("api/route", RouteOrchestratorView.as_view(), name="route-orchestrator"),
    path("api/route/history", RouteHistoryView.as_view(), name="route-history"),
    path("api/routes/search", RouteSearchView.as_view(), name="route-search"),
    path(
        "api/routes/search/confirm",
        RouteSearchConfirmView.as_view(),
        name="route-search-confirm",
    ),
    path("api/routes/metadata", RouteMetadataView.as_view(), name="route-metadata"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
