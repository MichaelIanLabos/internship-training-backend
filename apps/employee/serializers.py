from rest_framework import serializers
from django.db import transaction
from .models import Employee

class EmployeeCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        # AC: Exclude metadata and auto-generated fields from the request body
        exclude = ["employer", "is_delete", "employee_code"]

    def create(self, validated_data):
        # AC: Inject the authenticated user as the employer from the request context
        user = self.context["request"].user
        
        # AC: Wrap in an atomic transaction to prevent duplicate employee codes during concurrent requests
        with transaction.atomic():
            # AC: Scoped auto-generation (Format: EMP-0001)
            # Counts existing records for this specific employer to determine the next sequence
            count = Employee.objects.filter(employer=user).count()
            new_code = f"EMP-{(count + 1):04d}"
            
            return Employee.objects.create(
                employer=user, 
                employee_code=new_code, 
                **validated_data
            )

class EmployeeTableViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = "__all__"

    def to_representation(self, instance):
        # AC: Return only specific fields required for the frontend table view
        return {
            "id": instance.id,
            "employee_code": instance.employee_code,
            "first_name": instance.first_name,
            "last_name": instance.last_name,
            "email": instance.email,
            "employee_status": instance.employee_status,
            # If your model doesn't have created_at, you can remove this line 
            # or add a DateTimeField to your model.
            "created_at": getattr(instance, 'created_at', None) 
        }

class EmployeeRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        # AC: Exclude employer and is_delete for the full detail view response
        exclude = ["employer", "is_delete"]