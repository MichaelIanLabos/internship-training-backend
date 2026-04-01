from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.core.views import API
from .models import EmployeeMovement
from .serializers import MovementSerializer
from django.shortcuts import get_object_or_404

class MovementAPIView(API):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = EmployeeMovement.objects.filter(employee__user=request.user, is_deleted=False)

        status_filter = request.query_params.get('status')
        movement_type_filter = request.query_params.get('movement_type')
        employee_id_filter = request.query_params.get('employee_id')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if movement_type_filter:
            queryset = queryset.filter(movement_type=movement_type_filter)
        if employee_id_filter:
            queryset = queryset.filter(employee_id=employee_id_filter)

        serializer = MovementSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = MovementSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save(status='pending', requested_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MovementDetailAPIView(API):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        movement = get_object_or_404(EmployeeMovement, pk=pk, employee__user=request.user, is_deleted=False)
        serializer = MovementSerializer(movement)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
class MovementApproveAPIView(API):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        """Approve movement - only if status is pending."""
        movement = get_object_or_404(EmployeeMovement, pk=pk, employee__user=request.user, is_deleted=False)

        # Enforce state transition rule
        if movement.status != 'pending':
            return Response(
                {"detail": f"Cannot approve movement. Status is already {movement.status}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update record
        movement.status = 'approved'
        movement.approved_by = request.user
        movement.save()

        serializer = MovementSerializer(movement)
        return Response(serializer.data, status=status.HTTP_200_OK)