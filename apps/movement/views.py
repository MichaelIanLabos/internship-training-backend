from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.core.views import API
from .serializers import MovementSerializer

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
