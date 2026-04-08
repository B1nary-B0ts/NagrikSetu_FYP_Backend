from rest_framework.permissions import BasePermission

class RolePermission(BasePermission):
    """
    Generic role-based permission.
    Usage: set `required_roles` in the view.
    """

    def has_permission(self, request, view):
        # Must be logged in
        if not request.user or not request.user.is_authenticated:
            return False

        # Get roles required by the view
        required_roles = getattr(view, "required_roles", [])

        # If no roles specified → deny by default (safe)
        if not required_roles:
            return False

        return request.user.role in required_roles