import pytest
from unittest.mock import patch, MagicMock
import math
from rest_framework import status
from rest_framework.views import APIView
from django.urls import reverse

from apps.authentication.models import User
from apps.employee.models import Employee

"""
Employee View Tests (YS-04 & YS-05)

These tests validate the acceptance criteria for:

EmployeeAPIView:
- POST /api/employees/ creates an employee scoped to request.user
- GET /api/employees/ returns only the current user's non-deleted employees
- DELETE /api/employees/ soft-deletes employees by IDs
- Email uniqueness validation per user
- Search filtering across first_name, last_name, email
- Pagination via ObjectManager.generate_pagination()
- user and is_deleted never present in responses
- Records from other users never returned

EmployeeDetailAPIView:
- GET /api/employees/{id}/ returns full employee detail
- PATCH /api/employees/{id}/ updates employee with partial=True
- Email uniqueness check excludes current record on update
- Cannot access or update another user's employee (404)

Run tests with: pytest tests/test_employee_views.py -v

"""

EMPLOYEE_URL = "/api/employees/"

def _employee_detail_url(pk):
    return f"/api/employees/{pk}/"

def _employee_restore_url(pk):
    return f"/api/employees/{pk}/restore/"

def _create_employee(user, first_name="John", last_name="Doe",
                     email="john@example.com", employee_code="EMP-0001",
                     is_deleted=False, employment_status="active"):
    return Employee.objects.create(
        user=user,
        employee_code=employee_code,
        first_name=first_name,
        last_name=last_name,
        email=email,
        is_deleted=is_deleted,
        employment_status=employment_status,
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


# ── GET /api/employees/{id}/ ────────────────────────────────────────────

@pytest.mark.django_db
class TestEmployeeDetail:
    """GET /api/employees/{id}/"""

    def test_retrieve_own_employee(self, authenticated_client, test_user):
        """GET returns full employee detail for own record."""
        emp = _create_employee(test_user, email="jane@example.com")

        response = authenticated_client.get(_employee_detail_url(emp.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "jane@example.com"
        assert response.data["employee_code"] == emp.employee_code

    def test_retrieve_excludes_user_and_is_deleted(self, authenticated_client, test_user):
        """user and is_deleted not present in detail response."""
        emp = _create_employee(test_user, email="jane@example.com")

        response = authenticated_client.get(_employee_detail_url(emp.id))

        assert response.status_code == status.HTTP_200_OK
        assert "user" not in response.data
        assert "user_id" not in response.data
        assert "is_deleted" not in response.data

    def test_retrieve_other_users_employee_returns_404(self, authenticated_client, test_user):
        """Cannot access another user's employee — returns 404."""
        other_user = User.objects.create_user(
            email="other@example.com", password="pass1234",
            first_name="Other", last_name="User",
        )
        emp = _create_employee(other_user, email="theirs@example.com")

        response = authenticated_client.get(_employee_detail_url(emp.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_deleted_employee_returns_404(self, authenticated_client, test_user):
        """Soft-deleted employee returns 404."""
        emp = _create_employee(test_user, email="gone@example.com", is_deleted=True)

        response = authenticated_client.get(_employee_detail_url(emp.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_nonexistent_employee_returns_404(self, authenticated_client):
        """Non-existent ID returns 404."""
        response = authenticated_client.get(_employee_detail_url(99999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_unauthenticated_returns_401(self, api_client, test_user):
        """Unauthenticated GET detail returns 401."""
        emp = _create_employee(test_user, email="jane@example.com")

        response = api_client.get(_employee_detail_url(emp.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ── PATCH /api/employees/{id}/ ──────────────────────────────────────────

@pytest.mark.django_db
class TestEmployeeUpdate:
    """PATCH /api/employees/{id}/"""

    def test_partial_update_first_name(self, authenticated_client, test_user):
        """PATCH with partial=True updates only provided fields."""
        emp = _create_employee(test_user, first_name="Old", email="emp@example.com")

        response = authenticated_client.patch(
            _employee_detail_url(emp.id), {"first_name": "New"}
        )

        assert response.status_code == status.HTTP_200_OK
        emp.refresh_from_db()
        assert emp.first_name == "New"

    def test_update_email_to_own_current_email_returns_200(self, authenticated_client, test_user):
        """Updating email to own current email returns 200 (self-exclusion works)."""
        emp = _create_employee(test_user, email="same@example.com")

        response = authenticated_client.patch(
            _employee_detail_url(emp.id), {"email": "same@example.com"}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_update_email_to_another_employees_email_returns_400(self, authenticated_client, test_user):
        """Updating email to another employee's email returns 400."""
        _create_employee(test_user, email="taken@example.com", employee_code="EMP-0001")
        emp = _create_employee(test_user, email="mine@example.com", employee_code="EMP-0002")

        response = authenticated_client.patch(
            _employee_detail_url(emp.id), {"email": "taken@example.com"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_email_duplicate_case_insensitive(self, authenticated_client, test_user):
        """Email uniqueness on update is case-insensitive."""
        _create_employee(test_user, email="taken@example.com", employee_code="EMP-0001")
        emp = _create_employee(test_user, email="mine@example.com", employee_code="EMP-0002")

        response = authenticated_client.patch(
            _employee_detail_url(emp.id), {"email": "TAKEN@Example.COM"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_update_other_users_employee(self, authenticated_client, test_user):
        """Cannot update another user's employee — returns 404."""
        other_user = User.objects.create_user(
            email="other@example.com", password="pass1234",
            first_name="Other", last_name="User",
        )
        emp = _create_employee(other_user, email="theirs@example.com")

        response = authenticated_client.patch(
            _employee_detail_url(emp.id), {"first_name": "Hacked"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_deleted_employee_returns_404(self, authenticated_client, test_user):
        """Cannot update a soft-deleted employee."""
        emp = _create_employee(test_user, email="gone@example.com", is_deleted=True)

        response = authenticated_client.patch(
            _employee_detail_url(emp.id), {"first_name": "Revived"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_unauthenticated_returns_401(self, api_client, test_user):
        """Unauthenticated PATCH returns 401."""
        emp = _create_employee(test_user, email="emp@example.com")

        response = api_client.patch(
            _employee_detail_url(emp.id), {"first_name": "New"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_response_excludes_user_and_is_deleted(self, authenticated_client, test_user):
        """user and is_deleted not present in update response."""
        emp = _create_employee(test_user, email="emp@example.com")

        response = authenticated_client.patch(
            _employee_detail_url(emp.id), {"first_name": "Updated"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert "user" not in response.data
        assert "user_id" not in response.data
        assert "is_deleted" not in response.data


# ── DELETE /api/employees/ ──────────────────────────────────────────────

@pytest.mark.django_db
class TestEmployeeDelete:
    """DELETE /api/employees/"""

    def test_soft_delete_employees(self, authenticated_client, test_user):
        """DELETE soft-deletes employees by setting is_deleted=True."""
        emp = _create_employee(
            test_user, email="del@example.com", employment_status="inactive"
        )

        response = authenticated_client.delete(
            EMPLOYEE_URL, {"employee_ids": [emp.id]}
        )

        assert response.status_code == status.HTTP_200_OK
        emp.refresh_from_db()
        assert emp.is_deleted is True

    def test_bulk_soft_delete(self, authenticated_client, test_user):
        """DELETE can soft-delete multiple employees at once."""
        emp1 = _create_employee(
            test_user, email="a@example.com", employee_code="EMP-0001",
            employment_status="inactive",
        )
        emp2 = _create_employee(
            test_user, email="b@example.com", employee_code="EMP-0002",
            employment_status="inactive",
        )

        response = authenticated_client.delete(
            EMPLOYEE_URL, {"employee_ids": [emp1.id, emp2.id]}
        )

        assert response.status_code == status.HTTP_200_OK
        emp1.refresh_from_db()
        emp2.refresh_from_db()
        assert emp1.is_deleted is True
        assert emp2.is_deleted is True

    def test_delete_missing_employee_ids_returns_400(self, authenticated_client):
        """DELETE without employee_ids returns 400."""
        response = authenticated_client.delete(EMPLOYEE_URL, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_empty_employee_ids_returns_400(self, authenticated_client):
        """DELETE with empty employee_ids list returns 400."""
        response = authenticated_client.delete(
            EMPLOYEE_URL, {"employee_ids": []}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_delete_other_users_employees(self, authenticated_client, test_user):
        """Cross-tenant deletion impossible — other user's IDs are ignored."""
        other_user = User.objects.create_user(
            email="other@example.com", password="pass1234",
            first_name="Other", last_name="User",
        )
        emp = _create_employee(
            other_user, email="theirs@example.com", employment_status="inactive"
        )

        response = authenticated_client.delete(
            EMPLOYEE_URL, {"employee_ids": [emp.id]}
        )

        assert response.status_code == status.HTTP_200_OK
        emp.refresh_from_db()
        assert emp.is_deleted is False

    def test_deleted_records_excluded_from_list(self, authenticated_client, test_user):
        """Soft-deleted records no longer appear in the list endpoint."""
        emp = _create_employee(
            test_user, email="gone@example.com", employment_status="inactive"
        )

        authenticated_client.delete(
            EMPLOYEE_URL, {"employee_ids": [emp.id]}
        )
        response = authenticated_client.get(EMPLOYEE_URL)

        assert response.data["total_records"] == 0

    def test_never_hard_deletes(self, authenticated_client, test_user):
        """Uses .update(is_deleted=True) — record still exists in DB."""
        emp = _create_employee(
            test_user, email="soft@example.com", employment_status="inactive"
        )

        authenticated_client.delete(
            EMPLOYEE_URL, {"employee_ids": [emp.id]}
        )

        assert Employee.objects.filter(id=emp.id).exists()

    def test_delete_unauthenticated_returns_401(self, api_client, test_user):
        """Unauthenticated DELETE returns 401."""
        emp = _create_employee(
            test_user, email="del@example.com", employment_status="inactive"
        )

        response = api_client.delete(
            EMPLOYEE_URL, {"employee_ids": [emp.id]}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── Active employee deletion validation ─────────────────────────────

    def test_cannot_delete_active_employee(self, authenticated_client, test_user):
        """Active employees (employment_status=active) cannot be deleted."""
        emp = _create_employee(
            test_user, email="active@example.com", employment_status="active"
        )

        response = authenticated_client.delete(
            EMPLOYEE_URL, {"employee_ids": [emp.id]}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        emp.refresh_from_db()
        assert emp.is_deleted is False

    def test_bulk_delete_blocks_if_any_active(self, authenticated_client, test_user):
        """Bulk delete rejects entire request if any employee is active."""
        emp_inactive = _create_employee(
            test_user, email="inactive@example.com", employee_code="EMP-0001",
            employment_status="inactive",
        )
        emp_active = _create_employee(
            test_user, email="active@example.com", employee_code="EMP-0002",
            employment_status="active",
        )

        response = authenticated_client.delete(
            EMPLOYEE_URL, {"employee_ids": [emp_inactive.id, emp_active.id]}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        emp_inactive.refresh_from_db()
        emp_active.refresh_from_db()
        assert emp_inactive.is_deleted is False
        assert emp_active.is_deleted is False

    def test_active_delete_response_includes_names(self, authenticated_client, test_user):
        """400 response includes names of active employees blocking deletion."""
        emp = _create_employee(
            test_user, first_name="Jane", last_name="Doe",
            email="jane@example.com", employment_status="active",
        )

        response = authenticated_client.delete(
            EMPLOYEE_URL, {"employee_ids": [emp.id]}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "active_employees" in response.data
        assert "Jane Doe" in response.data["active_employees"]


# ── Edit Employee Modal (backend validation) ────────────────────────────

@pytest.mark.django_db
class TestEditEmployeeModal:
    """
    Backend tests supporting the Edit Employee modal acceptance criteria.
    Frontend-only concerns (modal open/close, inline display) are not
    tested here — only the API contracts that the modal depends on.
    """

    def test_detail_returns_all_fields_for_prepopulation(self, authenticated_client, test_user):
        """GET detail returns every field the edit form needs to pre-populate."""
        emp = _create_employee(
            test_user, first_name="Jane", last_name="Doe",
            email="jane@example.com", employee_code="EMP-0001",
        )

        response = authenticated_client.get(_employee_detail_url(emp.id))

        assert response.status_code == status.HTTP_200_OK
        for field in ("id", "employee_code", "first_name", "last_name",
                      "email", "employment_status", "created_at"):
            assert field in response.data, f"Missing field: {field}"

    def test_submit_no_changes_returns_200(self, authenticated_client, test_user):
        """Submitting with no changes returns success (no false errors)."""
        emp = _create_employee(
            test_user, first_name="Jane", last_name="Doe",
            email="jane@example.com",
        )

        response = authenticated_client.patch(
            _employee_detail_url(emp.id),
            {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
        )

        assert response.status_code == status.HTTP_200_OK

    def test_update_first_name_leaves_other_fields_unchanged(self, authenticated_client, test_user):
        """Updating first_name only saves the change and leaves all other fields unchanged."""
        emp = _create_employee(
            test_user, first_name="Jane", last_name="Doe",
            email="jane@example.com", employee_code="EMP-0001",
        )

        response = authenticated_client.patch(
            _employee_detail_url(emp.id), {"first_name": "Janet"}
        )

        assert response.status_code == status.HTTP_200_OK
        emp.refresh_from_db()
        assert emp.first_name == "Janet"
        assert emp.last_name == "Doe"
        assert emp.email == "jane@example.com"
        assert emp.employee_code == "EMP-0001"

    def test_update_own_email_returns_200(self, authenticated_client, test_user):
        """Updating email to the employee's own current email returns success."""
        emp = _create_employee(test_user, email="jane@example.com")

        response = authenticated_client.patch(
            _employee_detail_url(emp.id), {"email": "jane@example.com"}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_duplicate_email_returns_structured_error(self, authenticated_client, test_user):
        """Duplicate email returns a 400 with a detail message the frontend can display inline."""
        _create_employee(test_user, email="taken@example.com", employee_code="EMP-0001")
        emp = _create_employee(test_user, email="mine@example.com", employee_code="EMP-0002")

        response = authenticated_client.patch(
            _employee_detail_url(emp.id), {"email": "taken@example.com"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data

    def test_successful_update_reflects_new_values_in_response(self, authenticated_client, test_user):
        """Successful update response contains the updated values (no refetch needed)."""
        emp = _create_employee(
            test_user, first_name="Jane", last_name="Doe",
            email="jane@example.com",
        )

        response = authenticated_client.patch(
            _employee_detail_url(emp.id),
            {"first_name": "Janet", "last_name": "Smith"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Janet"
        assert response.data["last_name"] == "Smith"
        assert response.data["email"] == "jane@example.com"

    def test_employee_code_not_editable(self, authenticated_client, test_user):
        """employee_code cannot be changed via PATCH — it stays the same."""
        emp = _create_employee(
            test_user, email="jane@example.com", employee_code="EMP-0001",
        )

        response = authenticated_client.patch(
            _employee_detail_url(emp.id), {"employee_code": "HACKED-9999"}
        )

        assert response.status_code == status.HTTP_200_OK
        emp.refresh_from_db()
        assert emp.employee_code == "EMP-0001"

    def test_updated_values_visible_in_list(self, authenticated_client, test_user):
        """After a successful update, the list endpoint returns the new values."""
        emp = _create_employee(
            test_user, first_name="Jane", email="jane@example.com",
        )

        authenticated_client.patch(
            _employee_detail_url(emp.id), {"first_name": "Janet"}
        )
        response = authenticated_client.get(EMPLOYEE_URL)

        assert response.data["total_records"] == 1
        assert response.data["records"][0]["first_name"] == "Janet"

@pytest.mark.django_db
class TestEmployeeRestore:
    """POST /api/employees/{id}/restore/"""

    def test_restore_deleted_employee(self, authenticated_client, test_user):
        """Restoring a soft-deleted employee sets is_deleted=False."""
        emp = _create_employee(
            test_user, email="restore@example.com", is_deleted=True,
        )

        response = authenticated_client.post(_employee_restore_url(emp.id))

        assert response.status_code == status.HTTP_200_OK
        emp.refresh_from_db()
        assert emp.is_deleted is False

    def test_restore_returns_serialized_employee(self, authenticated_client, test_user):
        """Restore response contains the full serialized employee data."""
        emp = _create_employee(
            test_user, first_name="Jane", last_name="Doe",
            email="restore@example.com", employee_code="EMP-0001",
            is_deleted=True,
        )

        response = authenticated_client.post(_employee_restore_url(emp.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Jane"
        assert response.data["email"] == "restore@example.com"
        assert response.data["employee_code"] == "EMP-0001"

    def test_restore_response_excludes_user_and_is_deleted(self, authenticated_client, test_user):
        """user and is_deleted not present in restore response."""
        emp = _create_employee(
            test_user, email="restore@example.com", is_deleted=True,
        )

        response = authenticated_client.post(_employee_restore_url(emp.id))

        assert response.status_code == status.HTTP_200_OK
        assert "user" not in response.data
        assert "user_id" not in response.data
        assert "is_deleted" not in response.data

    def test_cannot_restore_non_deleted_employee(self, authenticated_client, test_user):
        """Restoring an already-active employee returns 404."""
        emp = _create_employee(
            test_user, email="active@example.com", is_deleted=False,
        )

        response = authenticated_client.post(_employee_restore_url(emp.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_restore_other_users_employee(self, authenticated_client, test_user):
        """Cross-tenant restore returns 404."""
        other_user = User.objects.create_user(
            email="other@example.com", password="pass1234",
            first_name="Other", last_name="User",
        )
        emp = _create_employee(
            other_user, email="theirs@example.com", is_deleted=True,
        )

        response = authenticated_client.post(_employee_restore_url(emp.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_restore_nonexistent_employee_returns_404(self, authenticated_client):
        """Non-existent ID returns 404."""
        response = authenticated_client.post(_employee_restore_url(99999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_restore_unauthenticated_returns_401(self, api_client, test_user):
        """Unauthenticated POST restore returns 401."""
        emp = _create_employee(
            test_user, email="restore@example.com", is_deleted=True,
        )

        response = api_client.post(_employee_restore_url(emp.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_restore_with_duplicate_email_returns_400(self, authenticated_client, test_user):
        """Cannot restore if an active employee already has the same email."""
        _create_employee(
            test_user, email="taken@example.com", employee_code="EMP-0001",
            is_deleted=False,
        )
        deleted_emp = _create_employee(
            test_user, email="taken@example.com", employee_code="EMP-0002",
            is_deleted=True,
        )

        response = authenticated_client.post(_employee_restore_url(deleted_emp.id))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data
        deleted_emp.refresh_from_db()
        assert deleted_emp.is_deleted is True

    def test_restored_employee_visible_in_list(self, authenticated_client, test_user):
        """After restore, the employee appears in the list endpoint."""
        emp = _create_employee(
            test_user, first_name="Restored", email="back@example.com",
            is_deleted=True,
        )

        authenticated_client.post(_employee_restore_url(emp.id))
        response = authenticated_client.get(EMPLOYEE_URL)

        assert response.data["total_records"] == 1
        assert response.data["records"][0]["first_name"] == "Restored"
