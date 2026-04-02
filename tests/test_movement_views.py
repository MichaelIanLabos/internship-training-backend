import pytest
from unittest.mock import MagicMock
import math
from rest_framework import status
from rest_framework.views import APIView

from apps.authentication.models import User
from apps.employee.models import Employee
from apps.movement.models import EmployeeMovement

"""
Movement View Tests (YS-14 BE-FE Integration)

These tests validate the acceptance criteria for:

MovementAPIView:
- POST /api/movements/ creates a movement scoped to request.user
- GET /api/movements/ returns only the current user's non-deleted movements
- Pagination via ObjectManager.generate_pagination()
- Search filtering across employee first_name, last_name
- Status and movement_type query param filters
- Response includes nested employee and user name fields
- is_deleted never present in responses

MovementDetailAPIView:
- GET /api/movements/{id}/ returns full movement detail
- PATCH /api/movements/{id}/ updates only pending movements with partial=True
- DELETE /api/movements/{id}/ soft-deletes only pending movements
- Cannot access or modify another user's movement (404)

MovementApproveAPIView:
- PATCH /api/movements/{id}/approve/ approves only pending movements

MovementRejectAPIView:
- PATCH /api/movements/{id}/reject/ rejects only pending movements
- Rejection remarks saved when provided

Run tests with: pytest tests/test_movement_views.py -v
"""

MOVEMENT_URL = "/api/movements/"


def _movement_detail_url(pk):
    return f"/api/movements/{pk}/"


def _movement_approve_url(pk):
    return f"/api/movements/{pk}/approve/"


def _movement_reject_url(pk):
    return f"/api/movements/{pk}/reject/"


def _create_employee(user, first_name="John", last_name="Doe",
                     email="john@example.com", employee_code="EMP-0001"):
    return Employee.objects.create(
        user=user,
        employee_code=employee_code,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )


def _create_movement(employee, requested_by, movement_type="transfer",
                     status_val="pending", remarks=None, is_deleted=False,
                     effective_date=None, current_department=None,
                     target_department=None, current_position=None,
                     new_position=None):
    return EmployeeMovement.objects.create(
        employee=employee,
        movement_type=movement_type,
        status=status_val,
        requested_by=requested_by,
        remarks=remarks,
        is_deleted=is_deleted,
        effective_date=effective_date,
        current_department=current_department,
        target_department=target_department,
        current_position=current_position,
        new_position=new_position,
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


# ── POST /api/movements/ ────────────────────────────────────────────────

@pytest.mark.django_db
class TestMovementCreate:
    """POST /api/movements/"""

    def test_create_movement_success(self, authenticated_client, test_user):
        """POST creates a movement with status=pending and requested_by=request.user."""
        emp = _create_employee(test_user)
        data = {
            "employee": emp.id,
            "movement_type": "transfer",
        }
        response = authenticated_client.post(MOVEMENT_URL, data)

        assert response.status_code == status.HTTP_201_CREATED
        mov = EmployeeMovement.objects.get(employee=emp)
        assert mov.status == "pending"
        assert mov.requested_by == test_user

    def test_create_movement_with_all_fields(self, authenticated_client, test_user):
        """POST accepts the new detail fields (effective_date, departments, positions)."""
        emp = _create_employee(test_user)
        data = {
            "employee": emp.id,
            "movement_type": "promotion",
            "effective_date": "2026-05-01",
            "current_department": "Engineering",
            "target_department": "Product",
            "current_position": "Developer",
            "new_position": "Lead Developer",
            "remarks": "Excellent performance",
        }
        response = authenticated_client.post(MOVEMENT_URL, data)

        assert response.status_code == status.HTTP_201_CREATED
        mov = EmployeeMovement.objects.get(employee=emp)
        assert str(mov.effective_date) == "2026-05-01"
        assert mov.current_department == "Engineering"
        assert mov.target_department == "Product"
        assert mov.current_position == "Developer"
        assert mov.new_position == "Lead Developer"

    def test_create_missing_required_fields_returns_400(self, authenticated_client):
        """POST with empty body returns 400."""
        response = authenticated_client.post(MOVEMENT_URL, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_invalid_movement_type_returns_400(self, authenticated_client, test_user):
        """POST with invalid movement_type returns 400."""
        emp = _create_employee(test_user)
        data = {
            "employee": emp.id,
            "movement_type": "invalid_type",
        }
        response = authenticated_client.post(MOVEMENT_URL, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_unauthenticated_returns_401(self, api_client, test_user):
        """Unauthenticated POST returns 401."""
        emp = _create_employee(test_user)
        data = {"employee": emp.id, "movement_type": "transfer"}

        response = api_client.post(MOVEMENT_URL, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_response_excludes_is_deleted(self, authenticated_client, test_user):
        """is_deleted not present in the create response."""
        emp = _create_employee(test_user)
        data = {"employee": emp.id, "movement_type": "transfer"}

        response = authenticated_client.post(MOVEMENT_URL, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert "is_deleted" not in response.data


# ── GET /api/movements/ ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestMovementList:
    """GET /api/movements/"""

    def test_list_returns_own_movements(self, authenticated_client, test_user):
        """GET returns only the current user's non-deleted movements."""
        emp = _create_employee(test_user)
        _create_movement(emp, test_user)
        _create_movement(emp, test_user, movement_type="promotion")

        response = authenticated_client.get(MOVEMENT_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_records"] == 2

    def test_does_not_return_other_users_movements(self, authenticated_client, test_user):
        """Records from other users never returned."""
        other_user = User.objects.create_user(
            email="other@example.com", password="pass1234",
            first_name="Other", last_name="User",
        )
        my_emp = _create_employee(test_user, email="mine@example.com", employee_code="EMP-0001")
        other_emp = _create_employee(other_user, email="theirs@example.com", employee_code="EMP-0002")
        _create_movement(my_emp, test_user)
        _create_movement(other_emp, other_user)

        response = authenticated_client.get(MOVEMENT_URL)

        assert response.data["total_records"] == 1

    def test_excludes_soft_deleted_movements(self, authenticated_client, test_user):
        """Soft-deleted records are hidden."""
        emp = _create_employee(test_user)
        _create_movement(emp, test_user)
        _create_movement(emp, test_user, is_deleted=True)

        response = authenticated_client.get(MOVEMENT_URL)

        assert response.data["total_records"] == 1

    def test_filter_by_status(self, authenticated_client, test_user):
        """?status= filters movements by status."""
        emp = _create_employee(test_user)
        _create_movement(emp, test_user, status_val="pending")
        _create_movement(emp, test_user, status_val="approved")

        response = authenticated_client.get(MOVEMENT_URL, {"status": "pending"})

        assert response.data["total_records"] == 1
        assert response.data["records"][0]["status"] == "pending"

    def test_filter_by_movement_type(self, authenticated_client, test_user):
        """?movement_type= filters movements by type."""
        emp = _create_employee(test_user)
        _create_movement(emp, test_user, movement_type="transfer")
        _create_movement(emp, test_user, movement_type="promotion")

        response = authenticated_client.get(MOVEMENT_URL, {"movement_type": "transfer"})

        assert response.data["total_records"] == 1
        assert response.data["records"][0]["movement_type"] == "transfer"

    def test_filter_by_employee_id(self, authenticated_client, test_user):
        """?employee_id= filters movements by employee."""
        emp1 = _create_employee(test_user, email="a@example.com", employee_code="EMP-0001")
        emp2 = _create_employee(test_user, email="b@example.com", employee_code="EMP-0002")
        _create_movement(emp1, test_user)
        _create_movement(emp2, test_user)

        response = authenticated_client.get(MOVEMENT_URL, {"employee_id": emp1.id})

        assert response.data["total_records"] == 1

    def test_search_by_employee_first_name(self, authenticated_client, test_user):
        """?search= filters by employee first_name."""
        emp1 = _create_employee(test_user, first_name="Alice", email="a@example.com", employee_code="EMP-0001")
        emp2 = _create_employee(test_user, first_name="Bob", email="b@example.com", employee_code="EMP-0002")
        _create_movement(emp1, test_user)
        _create_movement(emp2, test_user)

        response = authenticated_client.get(MOVEMENT_URL, {"search": "alice"})

        assert response.data["total_records"] == 1

    def test_search_by_employee_last_name(self, authenticated_client, test_user):
        """?search= filters by employee last_name."""
        emp1 = _create_employee(test_user, first_name="Alice", last_name="Smith",
                                email="a@example.com", employee_code="EMP-0001")
        emp2 = _create_employee(test_user, first_name="Bob", last_name="Jones",
                                email="b@example.com", employee_code="EMP-0002")
        _create_movement(emp1, test_user)
        _create_movement(emp2, test_user)

        response = authenticated_client.get(MOVEMENT_URL, {"search": "jones"})

        assert response.data["total_records"] == 1

    def test_search_is_case_insensitive(self, authenticated_client, test_user):
        """Search uses icontains — case should not matter."""
        emp = _create_employee(test_user, first_name="Alice")
        _create_movement(emp, test_user)

        response = authenticated_client.get(MOVEMENT_URL, {"search": "ALICE"})

        assert response.data["total_records"] == 1

    def test_search_no_results(self, authenticated_client, test_user):
        """Search with no matches returns empty records."""
        emp = _create_employee(test_user)
        _create_movement(emp, test_user)

        response = authenticated_client.get(MOVEMENT_URL, {"search": "zzz"})

        assert response.data["total_records"] == 0
        assert response.data["records"] == []

    def test_pagination_response_shape(self, authenticated_client, test_user):
        """Response contains total_records, total_pages, current_page, records."""
        emp = _create_employee(test_user)
        _create_movement(emp, test_user)

        response = authenticated_client.get(MOVEMENT_URL)

        assert "total_records" in response.data
        assert "total_pages" in response.data
        assert "current_page" in response.data
        assert "records" in response.data

    def test_pagination_defaults(self, authenticated_client, test_user):
        """Default page=1, page_size=10."""
        emp = _create_employee(test_user)
        for _ in range(3):
            _create_movement(emp, test_user)

        response = authenticated_client.get(MOVEMENT_URL)

        assert response.data["current_page"] == 1
        assert response.data["total_records"] == 3
        assert response.data["total_pages"] == 1
        assert len(response.data["records"]) == 3

    def test_pagination_limits_records(self, authenticated_client, test_user):
        """Requesting page_size=2 should only return 2 records per page."""
        emp = _create_employee(test_user)
        for _ in range(5):
            _create_movement(emp, test_user)

        response = authenticated_client.get(MOVEMENT_URL, {"page_size": 2})

        assert response.data["total_records"] == 5
        assert response.data["total_pages"] == 3
        assert len(response.data["records"]) == 2

    def test_pagination_second_page(self, authenticated_client, test_user):
        """Page 2 with page_size=2 returns the next set of records."""
        emp = _create_employee(test_user)
        for _ in range(5):
            _create_movement(emp, test_user)

        response = authenticated_client.get(MOVEMENT_URL, {"page": 2, "page_size": 2})

        assert response.data["current_page"] == 2
        assert len(response.data["records"]) == 2

    def test_response_includes_nested_employee_fields(self, authenticated_client, test_user):
        """Response records include employee_code, employee_first_name, employee_last_name."""
        emp = _create_employee(test_user, first_name="Jane", last_name="Doe",
                               employee_code="EMP-0001")
        _create_movement(emp, test_user)

        response = authenticated_client.get(MOVEMENT_URL)

        record = response.data["records"][0]
        assert record["employee_code"] == "EMP-0001"
        assert record["employee_first_name"] == "Jane"
        assert record["employee_last_name"] == "Doe"

    def test_response_includes_requested_by_name(self, authenticated_client, test_user):
        """Response records include requested_by_first_name and requested_by_last_name."""
        emp = _create_employee(test_user)
        _create_movement(emp, test_user)

        response = authenticated_client.get(MOVEMENT_URL)

        record = response.data["records"][0]
        assert record["requested_by_first_name"] == "Test"
        assert record["requested_by_last_name"] == "User"

    def test_response_excludes_is_deleted(self, authenticated_client, test_user):
        """is_deleted not present in response records."""
        emp = _create_employee(test_user)
        _create_movement(emp, test_user)

        response = authenticated_client.get(MOVEMENT_URL)

        record = response.data["records"][0]
        assert "is_deleted" not in record

    def test_unauthenticated_returns_401(self, api_client):
        """Unauthenticated GET returns 401."""
        response = api_client.get(MOVEMENT_URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ── GET /api/movements/{id}/ ────────────────────────────────────────────

@pytest.mark.django_db
class TestMovementDetail:
    """GET /api/movements/{id}/"""

    def test_retrieve_own_movement(self, authenticated_client, test_user):
        """GET returns full movement detail for own record."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, movement_type="promotion")

        response = authenticated_client.get(_movement_detail_url(mov.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["movement_type"] == "promotion"

    def test_retrieve_includes_nested_fields(self, authenticated_client, test_user):
        """Detail response includes nested employee and user name fields."""
        emp = _create_employee(test_user, first_name="Jane", last_name="Doe",
                               employee_code="EMP-0001")
        mov = _create_movement(emp, test_user)

        response = authenticated_client.get(_movement_detail_url(mov.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["employee_code"] == "EMP-0001"
        assert response.data["employee_first_name"] == "Jane"
        assert response.data["employee_last_name"] == "Doe"
        assert response.data["requested_by_first_name"] == "Test"
        assert response.data["requested_by_last_name"] == "User"

    def test_retrieve_excludes_is_deleted(self, authenticated_client, test_user):
        """is_deleted not present in detail response."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user)

        response = authenticated_client.get(_movement_detail_url(mov.id))

        assert response.status_code == status.HTTP_200_OK
        assert "is_deleted" not in response.data

    def test_retrieve_other_users_movement_returns_404(self, authenticated_client, test_user):
        """Cannot access another user's movement — returns 404."""
        other_user = User.objects.create_user(
            email="other@example.com", password="pass1234",
            first_name="Other", last_name="User",
        )
        other_emp = _create_employee(other_user, email="theirs@example.com")
        mov = _create_movement(other_emp, other_user)

        response = authenticated_client.get(_movement_detail_url(mov.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_deleted_movement_returns_404(self, authenticated_client, test_user):
        """Soft-deleted movement returns 404."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, is_deleted=True)

        response = authenticated_client.get(_movement_detail_url(mov.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_nonexistent_returns_404(self, authenticated_client):
        """Non-existent ID returns 404."""
        response = authenticated_client.get(_movement_detail_url(99999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_unauthenticated_returns_401(self, api_client, test_user):
        """Unauthenticated GET detail returns 401."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user)

        response = api_client.get(_movement_detail_url(mov.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ── PATCH /api/movements/{id}/ ──────────────────────────────────────────

@pytest.mark.django_db
class TestMovementUpdate:
    """PATCH /api/movements/{id}/"""

    def test_partial_update_pending_movement(self, authenticated_client, test_user):
        """PATCH updates a pending movement with partial=True."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, remarks="Original")

        response = authenticated_client.patch(
            _movement_detail_url(mov.id), {"remarks": "Updated"},
        )

        assert response.status_code == status.HTTP_200_OK
        mov.refresh_from_db()
        assert mov.remarks == "Updated"

    def test_update_movement_type(self, authenticated_client, test_user):
        """PATCH can change movement_type on a pending record."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, movement_type="transfer")

        response = authenticated_client.patch(
            _movement_detail_url(mov.id), {"movement_type": "promotion"},
        )

        assert response.status_code == status.HTTP_200_OK
        mov.refresh_from_db()
        assert mov.movement_type == "promotion"

    def test_update_new_detail_fields(self, authenticated_client, test_user):
        """PATCH can update effective_date, departments, positions."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user)

        response = authenticated_client.patch(
            _movement_detail_url(mov.id),
            {
                "effective_date": "2026-06-01",
                "current_department": "Engineering",
                "target_department": "Product",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        mov.refresh_from_db()
        assert str(mov.effective_date) == "2026-06-01"
        assert mov.current_department == "Engineering"
        assert mov.target_department == "Product"

    def test_cannot_update_approved_movement(self, authenticated_client, test_user):
        """PATCH on an approved movement returns 400."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, status_val="approved")

        response = authenticated_client.patch(
            _movement_detail_url(mov.id), {"remarks": "Try edit"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "pending" in response.data["detail"].lower()

    def test_cannot_update_rejected_movement(self, authenticated_client, test_user):
        """PATCH on a rejected movement returns 400."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, status_val="rejected")

        response = authenticated_client.patch(
            _movement_detail_url(mov.id), {"remarks": "Try edit"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_update_other_users_movement(self, authenticated_client, test_user):
        """Cannot update another user's movement — returns 404."""
        other_user = User.objects.create_user(
            email="other@example.com", password="pass1234",
            first_name="Other", last_name="User",
        )
        other_emp = _create_employee(other_user, email="theirs@example.com")
        mov = _create_movement(other_emp, other_user)

        response = authenticated_client.patch(
            _movement_detail_url(mov.id), {"remarks": "Hacked"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_update_deleted_movement(self, authenticated_client, test_user):
        """Cannot update a soft-deleted movement — returns 404."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, is_deleted=True)

        response = authenticated_client.patch(
            _movement_detail_url(mov.id), {"remarks": "Try edit"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_response_excludes_is_deleted(self, authenticated_client, test_user):
        """is_deleted not present in update response."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user)

        response = authenticated_client.patch(
            _movement_detail_url(mov.id), {"remarks": "Updated"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "is_deleted" not in response.data

    def test_update_unauthenticated_returns_401(self, api_client, test_user):
        """Unauthenticated PATCH returns 401."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user)

        response = api_client.patch(
            _movement_detail_url(mov.id), {"remarks": "Nope"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ── DELETE /api/movements/{id}/ ─────────────────────────────────────────

@pytest.mark.django_db
class TestMovementDelete:
    """DELETE /api/movements/{id}/"""

    def test_soft_delete_pending_movement(self, authenticated_client, test_user):
        """DELETE soft-deletes a pending movement."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user)

        response = authenticated_client.delete(_movement_detail_url(mov.id))

        assert response.status_code == status.HTTP_200_OK
        mov.refresh_from_db()
        assert mov.is_deleted is True

    def test_cannot_delete_approved_movement(self, authenticated_client, test_user):
        """DELETE on an approved movement returns 400."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, status_val="approved")

        response = authenticated_client.delete(_movement_detail_url(mov.id))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mov.refresh_from_db()
        assert mov.is_deleted is False

    def test_cannot_delete_rejected_movement(self, authenticated_client, test_user):
        """DELETE on a rejected movement returns 400."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, status_val="rejected")

        response = authenticated_client.delete(_movement_detail_url(mov.id))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mov.refresh_from_db()
        assert mov.is_deleted is False

    def test_cannot_delete_other_users_movement(self, authenticated_client, test_user):
        """Cross-tenant deletion returns 404."""
        other_user = User.objects.create_user(
            email="other@example.com", password="pass1234",
            first_name="Other", last_name="User",
        )
        other_emp = _create_employee(other_user, email="theirs@example.com")
        mov = _create_movement(other_emp, other_user)

        response = authenticated_client.delete(_movement_detail_url(mov.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        mov.refresh_from_db()
        assert mov.is_deleted is False

    def test_deleted_records_excluded_from_list(self, authenticated_client, test_user):
        """Soft-deleted records no longer appear in the list endpoint."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user)

        authenticated_client.delete(_movement_detail_url(mov.id))
        response = authenticated_client.get(MOVEMENT_URL)

        assert response.data["total_records"] == 0

    def test_never_hard_deletes(self, authenticated_client, test_user):
        """Uses is_deleted=True — record still exists in DB."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user)

        authenticated_client.delete(_movement_detail_url(mov.id))

        assert EmployeeMovement.objects.filter(id=mov.id).exists()

    def test_delete_unauthenticated_returns_401(self, api_client, test_user):
        """Unauthenticated DELETE returns 401."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user)

        response = api_client.delete(_movement_detail_url(mov.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_nonexistent_returns_404(self, authenticated_client):
        """Non-existent ID returns 404."""
        response = authenticated_client.delete(_movement_detail_url(99999))

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ── PATCH /api/movements/{id}/approve/ ──────────────────────────────────

@pytest.mark.django_db
class TestMovementApprove:
    """PATCH /api/movements/{id}/approve/"""

    def test_approve_pending_movement(self, authenticated_client, test_user):
        """Approve sets status=approved and approved_by=request.user."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user)

        response = authenticated_client.patch(_movement_approve_url(mov.id))

        assert response.status_code == status.HTTP_200_OK
        mov.refresh_from_db()
        assert mov.status == "approved"
        assert mov.approved_by == test_user

    def test_approve_returns_serialized_movement(self, authenticated_client, test_user):
        """Approve response includes full serialized movement data."""
        emp = _create_employee(test_user, first_name="Jane", last_name="Doe",
                               employee_code="EMP-0001")
        mov = _create_movement(emp, test_user)

        response = authenticated_client.patch(_movement_approve_url(mov.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "approved"
        assert response.data["employee_first_name"] == "Jane"

    def test_cannot_approve_already_approved(self, authenticated_client, test_user):
        """Cannot approve an already-approved movement."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, status_val="approved")

        response = authenticated_client.patch(_movement_approve_url(mov.id))

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_approve_rejected_movement(self, authenticated_client, test_user):
        """Cannot approve a rejected movement."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, status_val="rejected")

        response = authenticated_client.patch(_movement_approve_url(mov.id))

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_approve_deleted_movement(self, authenticated_client, test_user):
        """Cannot approve a soft-deleted movement — returns 404."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, is_deleted=True)

        response = authenticated_client.patch(_movement_approve_url(mov.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_approve_other_users_movement(self, authenticated_client, test_user):
        """Cannot approve another user's movement — returns 404."""
        other_user = User.objects.create_user(
            email="other@example.com", password="pass1234",
            first_name="Other", last_name="User",
        )
        other_emp = _create_employee(other_user, email="theirs@example.com")
        mov = _create_movement(other_emp, other_user)

        response = authenticated_client.patch(_movement_approve_url(mov.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_approve_unauthenticated_returns_401(self, api_client, test_user):
        """Unauthenticated PATCH approve returns 401."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user)

        response = api_client.patch(_movement_approve_url(mov.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ── PATCH /api/movements/{id}/reject/ ───────────────────────────────────

@pytest.mark.django_db
class TestMovementReject:
    """PATCH /api/movements/{id}/reject/"""

    def test_reject_pending_movement(self, authenticated_client, test_user):
        """Reject sets status=rejected and approved_by=request.user."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user)

        response = authenticated_client.patch(_movement_reject_url(mov.id))

        assert response.status_code == status.HTTP_200_OK
        mov.refresh_from_db()
        assert mov.status == "rejected"
        assert mov.approved_by == test_user

    def test_reject_with_remarks(self, authenticated_client, test_user):
        """Rejection remarks are saved when provided."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user)

        response = authenticated_client.patch(
            _movement_reject_url(mov.id),
            {"remarks": "Insufficient justification"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        mov.refresh_from_db()
        assert mov.remarks == "Insufficient justification"

    def test_reject_without_remarks_keeps_existing(self, authenticated_client, test_user):
        """Rejecting without remarks does not overwrite existing remarks."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, remarks="Original note")

        response = authenticated_client.patch(_movement_reject_url(mov.id))

        assert response.status_code == status.HTTP_200_OK
        mov.refresh_from_db()
        assert mov.remarks == "Original note"

    def test_reject_returns_serialized_movement(self, authenticated_client, test_user):
        """Reject response includes full serialized movement data."""
        emp = _create_employee(test_user, first_name="Jane", employee_code="EMP-0001")
        mov = _create_movement(emp, test_user)

        response = authenticated_client.patch(_movement_reject_url(mov.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "rejected"

    def test_cannot_reject_already_rejected(self, authenticated_client, test_user):
        """Cannot reject an already-rejected movement."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, status_val="rejected")

        response = authenticated_client.patch(_movement_reject_url(mov.id))

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_reject_approved_movement(self, authenticated_client, test_user):
        """Cannot reject an approved movement."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, status_val="approved")

        response = authenticated_client.patch(_movement_reject_url(mov.id))

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_reject_deleted_movement(self, authenticated_client, test_user):
        """Cannot reject a soft-deleted movement — returns 404."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user, is_deleted=True)

        response = authenticated_client.patch(_movement_reject_url(mov.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_reject_other_users_movement(self, authenticated_client, test_user):
        """Cannot reject another user's movement — returns 404."""
        other_user = User.objects.create_user(
            email="other@example.com", password="pass1234",
            first_name="Other", last_name="User",
        )
        other_emp = _create_employee(other_user, email="theirs@example.com")
        mov = _create_movement(other_emp, other_user)

        response = authenticated_client.patch(_movement_reject_url(mov.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_reject_unauthenticated_returns_401(self, api_client, test_user):
        """Unauthenticated PATCH reject returns 401."""
        emp = _create_employee(test_user)
        mov = _create_movement(emp, test_user)

        response = api_client.patch(_movement_reject_url(mov.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
