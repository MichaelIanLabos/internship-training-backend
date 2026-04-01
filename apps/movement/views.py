from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.shortcuts import get_object_or_404
from apps.core.views import API, ObjectManager
from .models import EmployeeMovement
from .serializers import MovementSerializer


class MovementAPIView(API, ObjectManager):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = EmployeeMovement.objects.select_related(
            'employee', 'requested_by', 'approved_by'
        ).filter(employee__user=request.user, is_deleted=False)

        status_filter = request.query_params.get('status')
        movement_type_filter = request.query_params.get('movement_type')
        employee_id_filter = request.query_params.get('employee_id')
        search_query = request.query_params.get('search', '')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if movement_type_filter:
            queryset = queryset.filter(movement_type=movement_type_filter)
        if employee_id_filter:
            queryset = queryset.filter(employee_id=employee_id_filter)
        if search_query:
            queryset = queryset.filter(
                Q(employee__first_name__icontains=search_query) |
                Q(employee__last_name__icontains=search_query)
            )

        current_page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))

        pagination_data = self.generate_pagination(
            current_page=current_page,
            page_size=page_size,
            records=queryset,
        )

        serializer = MovementSerializer(pagination_data['records'], many=True)
        pagination_data['records'] = serializer.data

        return Response(pagination_data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = MovementSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save(status='pending', requested_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MovementDetailAPIView(API):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        movement = get_object_or_404(
            EmployeeMovement.objects.select_related('employee', 'requested_by', 'approved_by'),
            pk=pk, employee__user=request.user, is_deleted=False,
        )
        serializer = MovementSerializer(movement)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        movement = get_object_or_404(
            EmployeeMovement.objects.select_related('employee', 'requested_by', 'approved_by'),
            pk=pk, employee__user=request.user, is_deleted=False,
        )
        if movement.status != 'pending':
            return Response(
                {"detail": f"Only pending records can be edited. This record is already {movement.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = MovementSerializer(movement, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        movement = get_object_or_404(
            EmployeeMovement.objects.select_related('employee'),
            pk=pk, employee__user=request.user, is_deleted=False,
        )
        
        if movement.status != 'pending':
            return Response(
                {"detail": f"Only pending records can be deleted. This record is already {movement.status}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        movement.is_deleted = True
        movement.save()
        return Response({"detail": "Movement deleted successfully."}, status=status.HTTP_200_OK)
        
class MovementApproveAPIView(API):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        """Approve movement - only if status is pending."""
        movement = get_object_or_404(
            EmployeeMovement.objects.select_related('employee', 'requested_by', 'approved_by'),
            pk=pk, employee__user=request.user, is_deleted=False,
        )

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

class MovementRejectAPIView(API):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        """Reject movement - only if status is pending."""
        movement = get_object_or_404(
            EmployeeMovement.objects.select_related('employee', 'requested_by', 'approved_by'),
            pk=pk, employee__user=request.user, is_deleted=False,
        )

        # Enforce state transition rule
        if movement.status != 'pending':
            return Response(
                {"detail": f"Cannot reject movement. Status is already {movement.status}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update record
        movement.status = 'rejected'
        movement.approved_by = request.user
        rejection_remarks = request.data.get('remarks')
        if rejection_remarks:
            movement.remarks = rejection_remarks
        movement.save()

        serializer = MovementSerializer(movement)
        return Response(serializer.data, status=status.HTTP_200_OK)