from rest_framework import serializers
from .models import EmployeeMovement
from apps.employee.models import Employee

class MovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeMovement
        fields = [
            'id', 'employee', 'movement_type', 'status', 
            'requested_by', 'approved_by', 'remarks', 
            'created_at', 'updated_at', 'is_deleted'
        ]
        read_only_fields = ['status', 'requested_by', 'approved_by', 'created_at', 'updated_at', 'is_deleted']

    def validate_movement_type(self, value):
        valid_types = ['promotion', 'transfer', 'resignation']
        if value.lower() not in valid_types:
            raise serializers.ValidationError("Invalid movement_type")
        return value.lower()

    def validate_employee(self, value):
        request = self.context.get('request')
        if not value:
            raise serializers.ValidationError("Employee is required.")
        # Employer scoping: ensure employee belongs to the authenticated user
        if request and value.user != request.user:
            raise serializers.ValidationError("Employee not found.")
        return value
