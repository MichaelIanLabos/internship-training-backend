from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.core.views import API, ObjectManager
from .models import Employee
from .serializers import (
    EmployeeCreateUpdateSerializer,
    EmployeeTableViewSerializer,
    EmployeeRetrieveSerializer,
)

class EmployeeAPIView(API, ObjectManager):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        AC: POST /api/employees/ creates an employee scoped to request.user
        """
        email = request.data.get("email")
        user = request.user

        if Employee.objects.filter(
            user=user,
            email__iexact=email,
            is_deleted=False
        ).exists():
            return Response(
                {"detail": "An active employee with this email already exists for your account."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = EmployeeCreateUpdateSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """
        AC: GET /api/employees/ returns only current user's non-deleted employees
        """
        current_page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        search_query = request.query_params.get("search", "")

        queryset = Employee.objects.filter(user=request.user, is_deleted=False)

        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )

        queryset = queryset.order_index("-created_at") if hasattr(queryset, 'order_index') else queryset.order_by("-created_at")

        pagination_data = self.generate_pagination(
            current_page=current_page,
            page_size=page_size,
            records=queryset
        )

        serializer = EmployeeTableViewSerializer(pagination_data["records"], many=True)
        pagination_data["records"] = serializer.data

        return Response(pagination_data, status=status.HTTP_200_OK)

    def delete(self, request):
        employee_ids = request.data.get("employee_ids")

        if not employee_ids:
            return Response(
                {"detail": "employee_ids is required and cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employees = Employee.objects.filter(
            id__in=employee_ids,
            user=request.user,
            is_deleted=False,
        )

        active_employees = employees.filter(employment_status="active")
        if active_employees.exists():
            active_names = [
                f"{emp.first_name} {emp.last_name}" for emp in active_employees
            ]
            return Response(
                {
                    "detail": "Cannot delete active employees. Change their status before deleting.",
                    "active_employees": active_names,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated = employees.update(is_deleted=True)

        return Response(
            {"detail": f"{updated} employee(s) deleted successfully."},
            status=status.HTTP_200_OK,
        )


class EmployeeDetailAPIView(API, ObjectManager):
    permission_classes = [IsAuthenticated]

    def get_object(self, user, pk):
        return get_object_or_404(Employee, pk=pk, user=user, is_deleted=False)

    def get(self, request, pk):
        employee = self.get_object(request.user, pk)
        serializer = EmployeeRetrieveSerializer(employee)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        employee = self.get_object(request.user, pk)

        new_email = request.data.get("email")
        if new_email:
            duplicate = (
                Employee.objects.filter(
                    user=request.user,
                    email__iexact=new_email,
                    is_deleted=False,
                )
                .exclude(id=employee.id)
                .exists()
            )
            if duplicate:
                return Response(
                    {"detail": "An active employee with this email already exists for your account."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = EmployeeCreateUpdateSerializer(
            employee,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmployeeRestoreAPIView(API):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk, user=request.user, is_deleted=True)

        if Employee.objects.filter(
            user=request.user,
            email__iexact=employee.email,
            is_deleted=False,
        ).exists():
            return Response(
                {"detail": "An active employee with this email already exists. Cannot restore."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee.is_deleted = False
        employee.save()

        serializer = EmployeeRetrieveSerializer(employee)
        return Response(serializer.data, status=status.HTTP_200_OK)
