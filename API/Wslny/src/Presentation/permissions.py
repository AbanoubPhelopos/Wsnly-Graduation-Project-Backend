from rest_framework import permissions
from src.Core.Domain.Constants.Roles import Roles

class IsAdminUser(permissions.BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == Roles.ADMIN)
