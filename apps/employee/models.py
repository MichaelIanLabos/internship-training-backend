from django.db import models
from django.conf import settings 

class Employee(models.Model):
    # Foreign Key: Links to the Employer (User)
    # Refers to 'employeer_id' in the ERD. In Django, the field name is 'employer'
    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="employees"
    )
    
    # Unique identifier for the employee. 
    # While Django provides an 'id' by default, we keep employee_code unique as per logic.
    employee_code = models.CharField(max_length=20, unique=True)
    
    first_name = models.CharField(max_length=150)
    middle_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150)
    
    email = models.EmailField()
    
    # The ERD specifies IntegerField for phone numbers. 
    # (Note: CharField is usually preferred for "+" symbols, but following the ERD here):
    phone_number = models.IntegerField(null=True, blank=True)
    
    hire_date = models.DateField()
    
    # employee_status (enum) - typically represented as an IntegerField in Django
    # Example mapping: 1 = Active, 2 = Inactive, etc.
    employee_status = models.IntegerField(default=1)
    
    # is_delete (Boolean) field for soft deletion as specified in the ERD
    is_delete = models.BooleanField(default=False)

    class Meta:
        db_table = "employees"

    def __str__(self):
        return f"{self.employee_code} - {self.last_name}"