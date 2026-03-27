from django.db import models
from django.conf import settings


class EmployeeMovement(models.Model):
    MOVEMENT_TYPES = (
        ('promotion', 'Promotion'),
        ('transfer', 'Transfer'),
        ('resignation', 'Resignation'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    employee = models.ForeignKey(
        'employee.Employee', 
        on_delete=models.CASCADE,
        related_name='movements'
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
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
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'employee_movement'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee} - {self.movement_type} ({self.status})"
