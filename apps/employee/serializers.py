from rest_framework import serializers
from django.db import transaction
from .models import Employee

class EmployeeCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        # FIX: Changed to "is_deleted" to match the test's assertion
        exclude = ["user", "is_deleted", "employee_code"]

    def create(self, validated_data):
        user = self.context["request"].user
        with transaction.atomic():
            count = Employee.objects.filter(user=user).count()
            new_code = f"EMP-{(count + 1):04d}"
            return Employee.objects.create(
                user=user, 
                employee_code=new_code, 
                **validated_data
            )

class EmployeeTableViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = "__all__"

    def to_representation(self, instance):
        # FIX: Changed key from "employee_status" to "employment_status" 
        # to fix the KeyError in the tests
        return {
            "id": instance.id,
            "employee_code": instance.employee_code,
            "first_name": instance.first_name,
            "last_name": instance.last_name,
            "email": instance.email,
            "employment_status": instance.employment_status,
            "created_at": instance.created_at
        }

class EmployeeRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        # FIX: Changed to "is_deleted"
        exclude = ["user", "is_deleted"]