import pytest
from unittest.mock import MagicMock
from django.db import connection
from apps.authentication.models import User
from apps.employee.models import Employee
from apps.employee.serializers import (
    EmployeeCreateUpdateSerializer,
    EmployeeTableViewSerializer,
    EmployeeRetrieveSerializer,
)

"""
Employee Serializer Unit Tests

These tests are to validate the acceptance criteria for YS-03:
- EmployeeCreateUpdateSerializer: exclude fields, create() with user injection, EMP code generation
- EmployeeTableViewSerializer: to_representation() returns only specified fields
- EmployeeRetrieveSerializer: exclude fields for detail view
- user and is_deleted are never exposed in any serializer response

note: please Run tests with: pytest tests/test_employee_serializers.py -v
"""


def _make_request(user):
    request = MagicMock()
    request.user = user
    return request


@pytest.mark.django_db
class TestEmployeeCreateUpdateSerializer:
    """
    EmployeeCreateUpdateSerializer created with exclude = ["user", "is_deleted", "employee_code"]
    """

    def test_excluded_fields(self):
        """Serializer must exclude user, is_deleted, and employee_code."""
        meta = EmployeeCreateUpdateSerializer.Meta
        assert "user" in meta.exclude
        assert "is_deleted" in meta.exclude
        assert "employee_code" in meta.exclude

    def test_user_not_writable(self, test_user):
        """
        AC: user_id injected from request context, never from request body.
        Passing 'user' in the input data must have no effect.
        """
        request = _make_request(test_user)
        other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
            first_name="Other",
            last_name="User",
        )
        data = {
            "user": other_user.id,
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
        }
        serializer = EmployeeCreateUpdateSerializer(
            data=data, context={"request": request}
        )
        assert serializer.is_valid(), serializer.errors
        employee = serializer.save()
        # The employee must belong to the authenticated user, not the spoofed one
        assert employee.user_id == test_user.id

    def test_create_injects_user_from_context(self, test_user):
        """
        create() injects user_id from self.context["request"].user.id
        """
        request = _make_request(test_user)
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
        }
        serializer = EmployeeCreateUpdateSerializer(
            data=data, context={"request": request}
        )
        assert serializer.is_valid(), serializer.errors
        employee = serializer.save()
        assert employee.user_id == test_user.id

    def test_create_auto_generates_employee_code(self, test_user):
        """
        Employee code auto-generated using format EMP-0001, scoped per user_id.
        """
        request = _make_request(test_user)
        data = {
            "first_name": "First",
            "last_name": "Employee",
            "email": "first@example.com",
        }
        serializer = EmployeeCreateUpdateSerializer(
            data=data, context={"request": request}
        )
        assert serializer.is_valid(), serializer.errors
        emp = serializer.save()
        assert emp.employee_code == "EMP-0001"

    def test_employee_code_increments(self, test_user):
        """Second employee for the same user should be EMP-0002."""
        request = _make_request(test_user)
        for i, name in enumerate(["Alice", "Bob"], start=1):
            data = {
                "first_name": name,
                "last_name": "Test",
                "email": f"{name.lower()}@example.com",
            }
            serializer = EmployeeCreateUpdateSerializer(
                data=data, context={"request": request}
            )
            assert serializer.is_valid(), serializer.errors
            emp = serializer.save()

        assert emp.employee_code == "EMP-0002"

    def test_employee_code_scoped_per_user(self, test_user):
        """
        AC: Employee code scoped per user_id.
        Two different users should each start at EMP-0001.
        """
        second_user = User.objects.create_user(
            email="second@example.com",
            password="testpass123",
            first_name="Second",
            last_name="User",
        )
        # Create one employee for test_user
        request1 = _make_request(test_user)
        ser1 = EmployeeCreateUpdateSerializer(
            data={
                "first_name": "A",
                "last_name": "A",
                "email": "a@example.com",
            },
            context={"request": request1},
        )
        assert ser1.is_valid(), ser1.errors
        ser1.save()

        # Create first employee for second_user — should also be EMP-0001
        request2 = _make_request(second_user)
        ser2 = EmployeeCreateUpdateSerializer(
            data={
                "first_name": "B",
                "last_name": "B",
                "email": "b@example.com",
            },
            context={"request": request2},
        )
        assert ser2.is_valid(), ser2.errors
        emp2 = ser2.save()
        assert emp2.employee_code == "EMP-0001"

    def test_create_uses_transaction_atomic(self):
        """
        AC: create() wrapped in transaction.atomic().
        Verify by inspecting the source code of create().
        """
        import inspect

        source = inspect.getsource(EmployeeCreateUpdateSerializer.create)
        assert "transaction.atomic" in source


@pytest.mark.django_db
class TestEmployeeTableViewSerializer:
    """
    EmployeeTableViewSerializer overrides to_representation() returning only: id, employee_code, first_name, last_name, email, employment_status, created_at
    """

    def _create_employee(self, user):
        return Employee.objects.create(
            user=user,
            employee_code="EMP-0001",
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            employment_status="active",
        )

    def test_to_representation_returns_expected_keys(self, test_user):
        """Only the 7 specified fields should appear in the output."""
        emp = self._create_employee(test_user)
        serializer = EmployeeTableViewSerializer(emp)
        data = serializer.data
        expected_keys = {
            "id",
            "employee_code",
            "first_name",
            "last_name",
            "email",
            "employment_status",
            "created_at",
        }
        assert set(data.keys()) == expected_keys

    def test_to_representation_values(self, test_user):
        """Field values should match the model instance."""
        emp = self._create_employee(test_user)
        data = EmployeeTableViewSerializer(emp).data
        assert data["id"] == emp.id
        assert data["employee_code"] == "EMP-0001"
        assert data["first_name"] == "Jane"
        assert data["last_name"] == "Smith"
        assert data["email"] == "jane@example.com"
        assert data["employment_status"] == "active"

    def test_user_not_in_table_view(self, test_user):
        """user is never exposed."""
        emp = self._create_employee(test_user)
        data = EmployeeTableViewSerializer(emp).data
        assert "user" not in data
        assert "user_id" not in data

    def test_is_deleted_not_in_table_view(self, test_user):
        """is_deleted is never exposed."""
        emp = self._create_employee(test_user)
        data = EmployeeTableViewSerializer(emp).data
        assert "is_deleted" not in data


@pytest.mark.django_db
class TestEmployeeRetrieveSerializer:
    """
    EmployeeRetrieveSerializer created with exclude = ["user", "is_deleted"] for full detail view.
    """

    def _create_employee(self, user):
        return Employee.objects.create(
            user=user,
            employee_code="EMP-0001",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            employment_status="active",
        )

    def test_excluded_fields(self):
        """Serializer must exclude user and is_deleted."""
        meta = EmployeeRetrieveSerializer.Meta
        assert "user" in meta.exclude
        assert "is_deleted" in meta.exclude

    def test_includes_all_detail_fields(self, test_user):
        """Full detail view should include all non-excluded fields."""
        emp = self._create_employee(test_user)
        data = EmployeeRetrieveSerializer(emp).data
        for field in ["id", "employee_code", "first_name", "last_name",
                       "email", "employment_status", "created_at"]:
            assert field in data, f"Missing field: {field}"

    def test_user_not_exposed(self, test_user):
        """user is never exposed in any serializer response."""
        emp = self._create_employee(test_user)
        data = EmployeeRetrieveSerializer(emp).data
        assert "user" not in data
        assert "user_id" not in data

    def test_is_deleted_not_exposed(self, test_user):
        """is_deleted is never exposed in any serializer response."""
        emp = self._create_employee(test_user)
        data = EmployeeRetrieveSerializer(emp).data
        assert "is_deleted" not in data
