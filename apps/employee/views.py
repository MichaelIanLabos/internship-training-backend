from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

# These base classes (API, ObjectManager) are expected from your core app
from apps.core.views import API, ObjectManager
from .models import Employee
from .serializers import EmployeeCreateUpdateSerializer, EmployeeTableViewSerializer

class EmployeeAPIView(API, ObjectManager):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        AC: POST /api/employees/ creates an employee scoped to request.user
        """
        email = request.data.get("email")
        user = request.user

        # AC: Email uniqueness check per user_id and non-deleted records
        if Employee.objects.filter(
            user=user, 
            email__iexact=email, 
            is_deleted=False
        ).exists():
            return Response(
                {"detail": "An active employee with this email already exists for your account."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # AC: user_id sourced from request.user (passed via context to serializer)
        serializer = EmployeeCreateUpdateSerializer(
            data=request.data, 
            context={"request": request}
        )
        
        if serializer.is_valid():
            # AC: employee_code auto-generated inside serializer.save() -> create()
            serializer.save()
            # AC: user and is_deleted not present in response (handled by Serializer Meta)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """
        AC: GET /api/employees/ returns only current user's non-deleted employees
        """
        # AC: Extract pagination params
        current_page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        search_query = request.query_params.get("search", "")

        # AC: Base filter: Current user's records that are not deleted
        queryset = Employee.objects.filter(user=request.user, is_deleted=False)

        # AC: ?search= filters across first_name, last_name, and email using Q
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )

        # Sorting by newest first is generally expected for table views
        queryset = queryset.order_index("-created_at") if hasattr(queryset, 'order_index') else queryset.order_by("-created_at")

        # AC: Pagination applied via ObjectManager method
        # AC: Expected Shape: { total_records, total_pages, current_page, records: [] }
        pagination_data = self.generate_pagination(
            current_page=current_page,
            page_size=page_size,
            records=queryset
        )

        # Serialize the 'records' part of the pagination
        serializer = EmployeeTableViewSerializer(pagination_data["records"], many=True)
        pagination_data["records"] = serializer.data

        return Response(pagination_data, status=status.HTTP_200_OK)