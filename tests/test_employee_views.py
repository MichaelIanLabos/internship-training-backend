import pytest
from unittest.mock import patch, MagicMock
import math
from rest_framework import status
from rest_framework.views import APIView
from django.urls import reverse

from apps.authentication.models import User
from apps.employee.models import Employee

"""
Employee View Tests (YS-04)

These tests validate the acceptance criteria for the EmployeeAPIView:
- POST /api/employees/ creates an employee scoped to request.user
- GET /api/employees/ returns only the current user's non-deleted employees
- Email uniqueness validation per user
- Search filtering across first_name, last_name, email
- Pagination via ObjectManager.generate_pagination()
- user and is_deleted never present in responses
- Records from other users never returned

Run tests with: pytest tests/test_employee_views.py -v or

./venv/bin/pytest tests/test_employee_views.py::TestEmployeeCreate::test_create_employee_success -v

"""

EMPLOYEE_URL = "/api/employees/"


def _create_employee(user, first_name="John", last_name="Doe",
                     email="john@example.com", employee_code="EMP-0001",
                     is_deleted=False):
    return Employee.objects.create(
        user=user,
        employee_code=employee_code,
        first_name=first_name,
        last_name=last_name,
        email=email,
        is_deleted=is_deleted,
    )


class _ObjectManagerStub:
    def generate_pagination(self, current_page, page_size, records):
        total = records.count()
        total_pages = max(1, math.ceil(total / page_size))
        start = (current_page - 1) * page_size
        end = start + page_size
        return {
            "total_records": total,
            "total_pages": total_pages,
            "current_page": current_page,
            "records": records[start:end],
        }


_core_views_mock = MagicMock()
_core_views_mock.API = APIView
_core_views_mock.ObjectManager = _ObjectManagerStub

import sys
sys.modules.setdefault("apps.core.views", _core_views_mock)


@pytest.mark.django_db
class TestEmployeeCreate:
    """POST /api/employees/"""

    def test_create_employee_success(self, authenticated_client, test_user):
        """POST creates an employee scoped to request.user and returns 201."""
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
        }
        response = authenticated_client.post(EMPLOYEE_URL, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Employee.objects.filter(user=test_user, email="jane@example.com").exists()

    def test_user_sourced_from_request(self, authenticated_client, test_user):
        """user_id always sourced from request.user.id — never from request body."""
        other_user = User.objects.create_user(
            email="other@example.com", password="pass1234",
            first_name="Other", last_name="User",
        )
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
            "user": other_user.id,
        }
        response = authenticated_client.post(EMPLOYEE_URL, data)

        assert response.status_code == status.HTTP_201_CREATED
        emp = Employee.objects.get(email="jane@example.com")
        assert emp.user_id == test_user.id

    def test_employee_code_auto_generated(self, authenticated_client, test_user):
        """employee_code auto-generated on create (e.g. EMP-0001)."""
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
        }
        response = authenticated_client.post(EMPLOYEE_URL, data)

        assert response.status_code == status.HTTP_201_CREATED
        emp = Employee.objects.get(user=test_user, email="jane@example.com")
        assert emp.employee_code == "EMP-0001"

    def test_duplicate_email_same_user_returns_400(self, authenticated_client, test_user):
        """Email uniqueness checked before saving — returns 400 if duplicate."""
        _create_employee(test_user, email="dup@example.com")

        data = {
            "first_name": "Another",
            "last_name": "Person",
            "email": "dup@example.com",
        }
        response = authenticated_client.post(EMPLOYEE_URL, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_email_case_insensitive(self, authenticated_client, test_user):
        """Duplicate check is case-insensitive (email__iexact)."""
        _create_employee(test_user, email="dup@example.com")

        data = {
            "first_name": "Another",
            "last_name": "Person",
            "email": "DUP@Example.COM",
        }
        response = authenticated_client.post(EMPLOYEE_URL, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_email_different_user_returns_201(self, authenticated_client, test_user):
        """Duplicate email for a different user_id is allowed and returns 201."""
        other_user = User.objects.create_user(
            email="other@example.com", password="pass1234",
            first_name="Other", last_name="User",
        )
        _create_employee(other_user, email="shared@example.com")

        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "shared@example.com",
        }
        response = authenticated_client.post(EMPLOYEE_URL, data)

        assert response.status_code == status.HTTP_201_CREATED

    def test_soft_deleted_email_allows_recreation(self, authenticated_client, test_user):
        """
        A soft-deleted employee with the same email should NOT trigger the
        duplicate check (is_deleted=False filter).
        """
        _create_employee(test_user, email="old@example.com", is_deleted=True)

        data = {
            "first_name": "Revived",
            "last_name": "Employee",
            "email": "old@example.com",
        }
        response = authenticated_client.post(EMPLOYEE_URL, data)

        assert response.status_code == status.HTTP_201_CREATED

    def test_response_excludes_user_and_is_deleted(self, authenticated_client, test_user):
        """user and is_deleted not present in the response."""
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
        }
        response = authenticated_client.post(EMPLOYEE_URL, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert "user" not in response.data
        assert "user_id" not in response.data
        assert "is_deleted" not in response.data

    def test_unauthenticated_returns_401(self, api_client):
        """Unauthenticated POST returns 401."""
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
        }
        response = api_client.post(EMPLOYEE_URL, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_required_fields_returns_400(self, authenticated_client):
        """
        Sending an empty body should return 400 for missing required fields.
        """
        response = authenticated_client.post(EMPLOYEE_URL, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ── GET /api/employees/ ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestEmployeeList:
    """GET /api/employees/"""

    def test_list_returns_own_employees(self, authenticated_client, test_user):
        """GET returns only the current user's non-deleted employees."""
        _create_employee(test_user, first_name="Alice", email="alice@example.com",
                         employee_code="EMP-0001")
        _create_employee(test_user, first_name="Bob", email="bob@example.com",
                         employee_code="EMP-0002")

        response = authenticated_client.get(EMPLOYEE_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_records"] == 2

    def test_does_not_return_other_users_employees(self, authenticated_client, test_user):
        """Records from other users never returned."""
        other_user = User.objects.create_user(
            email="other@example.com", password="pass1234",
            first_name="Other", last_name="User",
        )
        _create_employee(test_user, email="mine@example.com", employee_code="EMP-0001")
        _create_employee(other_user, email="theirs@example.com", employee_code="EMP-0001")

        response = authenticated_client.get(EMPLOYEE_URL)

        assert response.data["total_records"] == 1
        emails = [r["email"] for r in response.data["records"]]
        assert "mine@example.com" in emails
        assert "theirs@example.com" not in emails

    def test_excludes_soft_deleted_employees(self, authenticated_client, test_user):
        """Soft-deleted records are hidden (is_deleted=False filter)."""
        _create_employee(test_user, email="active@example.com",
                         employee_code="EMP-0001")
        _create_employee(test_user, email="deleted@example.com",
                         employee_code="EMP-0002", is_deleted=True)

        response = authenticated_client.get(EMPLOYEE_URL)

        assert response.data["total_records"] == 1
        assert response.data["records"][0]["email"] == "active@example.com"

    def test_search_by_first_name(self, authenticated_client, test_user):
        """?search= filters by first_name."""
        _create_employee(test_user, first_name="Alice", last_name="Smith",
                         email="alice@example.com", employee_code="EMP-0001")
        _create_employee(test_user, first_name="Bob", last_name="Jones",
                         email="bob@example.com", employee_code="EMP-0002")

        response = authenticated_client.get(EMPLOYEE_URL, {"search": "alice"})

        assert response.data["total_records"] == 1
        assert response.data["records"][0]["first_name"] == "Alice"

    def test_search_by_last_name(self, authenticated_client, test_user):
        """?search= filters by last_name."""
        _create_employee(test_user, first_name="Alice", last_name="Smith",
                         email="alice@example.com", employee_code="EMP-0001")
        _create_employee(test_user, first_name="Bob", last_name="Jones",
                         email="bob@example.com", employee_code="EMP-0002")

        response = authenticated_client.get(EMPLOYEE_URL, {"search": "jones"})

        assert response.data["total_records"] == 1
        assert response.data["records"][0]["last_name"] == "Jones"

    def test_search_by_email(self, authenticated_client, test_user):
        """?search= filters by email."""
        _create_employee(test_user, first_name="Alice", last_name="Smith",
                         email="alice@corp.com", employee_code="EMP-0001")
        _create_employee(test_user, first_name="Bob", last_name="Jones",
                         email="bob@other.com", employee_code="EMP-0002")

        response = authenticated_client.get(EMPLOYEE_URL, {"search": "corp"})

        assert response.data["total_records"] == 1
        assert response.data["records"][0]["email"] == "alice@corp.com"

    def test_search_is_case_insensitive(self, authenticated_client, test_user):
        """Search uses icontains — case should not matter."""
        _create_employee(test_user, first_name="Alice", email="alice@example.com",
                         employee_code="EMP-0001")

        response = authenticated_client.get(EMPLOYEE_URL, {"search": "ALICE"})

        assert response.data["total_records"] == 1

    def test_search_no_results(self, authenticated_client, test_user):
        """Search with no matches returns empty records."""
        _create_employee(test_user, first_name="Alice", email="alice@example.com",
                         employee_code="EMP-0001")

        response = authenticated_client.get(EMPLOYEE_URL, {"search": "zzz"})

        assert response.data["total_records"] == 0
        assert response.data["records"] == []

    def test_pagination_response_shape(self, authenticated_client, test_user):
        """Response contains total_records, total_pages, current_page, records."""
        _create_employee(test_user, email="a@example.com", employee_code="EMP-0001")

        response = authenticated_client.get(EMPLOYEE_URL)

        assert "total_records" in response.data
        assert "total_pages" in response.data
        assert "current_page" in response.data
        assert "records" in response.data

    def test_pagination_defaults(self, authenticated_client, test_user):
        """Default page=1, page_size=10."""
        for i in range(3):
            _create_employee(test_user, first_name=f"Emp{i}",
                             email=f"emp{i}@example.com",
                             employee_code=f"EMP-{i+1:04d}")

        response = authenticated_client.get(EMPLOYEE_URL)

        assert response.data["current_page"] == 1
        assert response.data["total_records"] == 3
        assert response.data["total_pages"] == 1
        assert len(response.data["records"]) == 3

    def test_pagination_limits_records(self, authenticated_client, test_user):
        """Requesting page_size=2 should only return 2 records per page."""
        for i in range(5):
            _create_employee(test_user, first_name=f"Emp{i}",
                             email=f"emp{i}@example.com",
                             employee_code=f"EMP-{i+1:04d}")

        response = authenticated_client.get(EMPLOYEE_URL, {"page_size": 2})

        assert response.data["total_records"] == 5
        assert response.data["total_pages"] == 3
        assert len(response.data["records"]) == 2

    def test_pagination_second_page(self, authenticated_client, test_user):
        """Page 2 with page_size=2 should return the next set of records."""
        for i in range(5):
            _create_employee(test_user, first_name=f"Emp{i}",
                             email=f"emp{i}@example.com",
                             employee_code=f"EMP-{i+1:04d}")

        response = authenticated_client.get(EMPLOYEE_URL, {"page": 2, "page_size": 2})

        assert response.data["current_page"] == 2
        assert len(response.data["records"]) == 2

    def test_records_exclude_user_and_is_deleted(self, authenticated_client, test_user):
        """user and is_deleted not present in the response records."""
        _create_employee(test_user, email="a@example.com", employee_code="EMP-0001")

        response = authenticated_client.get(EMPLOYEE_URL)

        record = response.data["records"][0]
        assert "user" not in record
        assert "user_id" not in record
        assert "is_deleted" not in record

    def test_unauthenticated_returns_401(self, api_client):
        """Unauthenticated GET returns 401."""
        response = api_client.get(EMPLOYEE_URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
