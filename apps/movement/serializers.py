from rest_framework import serializers
from .models import EmployeeMovement
from apps.employee.models import Employee

class MovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeMovement
        fields = '__all__'
        read_only_fields = ['status', 'requested_by', 'approved_by', 'created_at', 'updated_at']
