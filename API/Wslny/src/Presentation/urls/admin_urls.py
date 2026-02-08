from django.urls import path
from src.Presentation.views.admin_views import ChangeUserRoleView, UserListView

urlpatterns = [
    path('admin/change-role', ChangeUserRoleView.as_view(), name='change-role'),
    path('admin/users', UserListView.as_view(), name='list-users'),
]
