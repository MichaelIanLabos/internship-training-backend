from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from apps.core.views import API, ObjectManager
from .serializers import MovementSerializer
from .models import EmployeeMovement

class MovementAPIView(API, ObjectManager):
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

    def get(self, request):
        """
        List movements for the authenticated employer (user) excluding soft-deleted records.
        """
        current_page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        
        # Scoped to employer's employees and not deleted
        queryset = EmployeeMovement.objects.filter(
            employee__user=request.user, 
            is_deleted=False
        )
        
        pagination_data = self.generate_pagination(
            current_page=current_page,
            page_size=page_size,
            records=queryset
        )
        
        serializer = MovementSerializer(pagination_data["records"], many=True)
        pagination_data["records"] = serializer.data
        
        return Response(pagination_data, status=status.HTTP_200_OK)


class MovementDetailAPIView(API):
    permission_classes = [IsAuthenticated]

    def get_object(self, user, pk):
        return get_object_or_404(
            EmployeeMovement, 
            pk=pk, 
            employee__user=user, 
            is_deleted=False
        )

    def get(self, request, pk):
        movement = self.get_object(request.user, pk)
        serializer = MovementSerializer(movement)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        movement = self.get_object(request.user, pk)
        
        if movement.status != 'pending':
            return Response(
                {"detail": f"Cannot delete movement because its status is {movement.status}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        movement.is_deleted = True
        movement.save()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
