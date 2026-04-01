from rest_framework import serializers
from .models import EmployeeMovement


class MovementSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_first_name = serializers.CharField(source='employee.first_name', read_only=True)
    employee_last_name = serializers.CharField(source='employee.last_name', read_only=True)
    requested_by_first_name = serializers.CharField(source='requested_by.first_name', read_only=True)
    requested_by_last_name = serializers.CharField(source='requested_by.last_name', read_only=True)
    approved_by_first_name = serializers.CharField(source='approved_by.first_name', read_only=True, default='')
    approved_by_last_name = serializers.CharField(source='approved_by.last_name', read_only=True, default='')

    class Meta:
        model = EmployeeMovement
        exclude = ['is_deleted']
        read_only_fields = [
            'status', 'requested_by', 'approved_by', 'created_at', 'updated_at',
            'employee_code', 'employee_first_name', 'employee_last_name',
            'requested_by_first_name', 'requested_by_last_name',
            'approved_by_first_name', 'approved_by_last_name',
        ]
