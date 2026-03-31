from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions
from rest_framework.response import Response
from apps.core.views import API
from .models import EmployeeMovement
from .serializers import MovementSerializer
from .permissions import IsMovementEmployeeEmployer

class MovementAPIView(API):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MovementSerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save(
                status='pending',
                requested_by=request.user
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MovementApprovalAPIView(API):
    permission_classes = [permissions.IsAuthenticated, IsMovementEmployeeEmployer]

    def patch(self, request, pk):
        """
        AC: PATCH /api/movements/{id}/approve/
        Restrict to authorized users (the employer) via IsMovementEmployeeEmployer
        Check status == pending before approving
        Set status = approved, approved_by = request.user
        Returns 200 on success
        Blocks if status is already approved or rejected (400)
        Unauthorized user returns 403 (handled by permission class)
        Cross-tenant access returns 403 (via permission class) or 404 (if ID not found)
        """
        # We fetch the movement first to check for existence
        movement = get_object_or_404(EmployeeMovement, pk=pk, is_deleted=False)

        # DRF permission check calls has_object_permission which checks employer ownership
        self.check_object_permissions(request, movement)

        if movement.status != 'pending':
            return Response(
                {"detail": f"Cannot approve movement with status '{movement.status}'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            movement.status = 'approved'
            movement.approved_by = request.user
            movement.save()

        serializer = MovementSerializer(movement)
        return Response(serializer.data, status=status.HTTP_200_OK)
