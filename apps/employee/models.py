from django.db import models
from django.conf import settings

class Employee(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    employee_code = models.CharField(max_length=20)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField()
    employment_status = models.CharField(max_length=50, default="active")
    # MUST be is_deleted to satisfy the test assertions
    is_deleted = models.BooleanField(default=False) 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "employee"