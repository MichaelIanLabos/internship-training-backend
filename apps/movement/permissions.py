from rest_framework import permissions

class IsMovementEmployeeEmployer(permissions.BasePermission):
    """
    Custom permission to only allow employers of an employee to approve or reject their movements.
    """

    def has_object_permission(self, request, view, obj):
        # The 'employer' is the user associated with the employee
        return obj.employee.user == request.user
