from django.db import models
from django.conf import settings
from apps.employee.models import Employee

class EmployeeMovement(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=100)
    status = models.CharField(max_length=50, default='pending')
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='requested_movements'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_movements'
    )
    remarks = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "employee_movement"
