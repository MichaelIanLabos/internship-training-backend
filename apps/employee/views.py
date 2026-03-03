from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Employee
from .serializers import (
    EmployeeCreateUpdateSerializer, 
    EmployeeTableViewSerializer,
    EmployeeRetrieveSerializer
)

# We use standard APIView since the custom API base class is missing
class EmployeeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Multi-tenancy: Always scope to the logged-in user (employer)
            employer_id = request.user.id
            email = request.data.get("email")

            # Validate Email Uniqueness per Employer
            if Employee.objects.filter(employer_id=employer_id, email__iexact=email, is_delete=False).exists():
                return Response({"error": "An employee with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)

            serializer = EmployeeCreateUpdateSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response({"message": "Employee created successfully."}, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        try:
            employer_id = request.user.id
            # Filter records for this employer that are not deleted
            employees = Employee.objects.filter(employer_id=employer_id, is_delete=False).order_by("-id")

            # Simple Search Logic
            search = request.query_params.get("search")
            if search:
                employees = employees.filter(
                    Q(first_name__icontains=search) | 
                    Q(last_name__icontains=search) | 
                    Q(email__icontains=search)
                )

            # Manual Pagination (Default: 10)
            # If you don't have the ObjectManager, we can just return all for now
            # or implement simple slicing.
            serializer = EmployeeTableViewSerializer(employees, many=True)
            return Response({"records": serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmployeeDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, employer_id, pk):
        try:
            return Employee.objects.get(employer_id=employer_id, pk=pk, is_delete=False)
        except Employee.DoesNotExist:
            return None

    def get(self, request, pk):
        instance = self.get_object(request.user.id, pk)
        if not instance:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = EmployeeRetrieveSerializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        instance = self.get_object(request.user.id, pk)
        if not instance:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = EmployeeCreateUpdateSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Employee updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        instance = self.get_object(request.user.id, pk)
        if not instance:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Soft Delete Logic
        instance.is_delete = True
        instance.save()
        return Response({"message": "Employee deleted successfully."}, status=status.HTTP_200_OK)