import pytest
from django.urls import reverse
from rest_framework import status
from apps.authentication.models import User

"""
Authentication Test Suite

These tests define what your authentication system should do.
Your goal: Make all these tests pass! ✅

Run tests with: pytest
Run specific test: pytest tests/test_authentication.py::TestRegistration::test_register_user_success
Run with coverage: pytest --cov=apps

Test-Driven Development (TDD):
1. Read the test to understand requirements
2. Write code to make the test pass
3. Refactor if needed
4. Move to next test
"""


@pytest.mark.django_db
class TestRegistration:
    """
    Test cases for user registration

    TODO for Interns:
    Implement the RegisterView and RegisterSerializer to make these tests pass.
    """

    def test_register_user_success(self, api_client):
        """
        Test successful user registration

        Requirements:
        - Accept POST request with user data
        - Create user in database with hashed password
        - Return 201 Created status
        - Return user data (without password)
        - Return success message
        """
        url = reverse('register')
        data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'strongpass123',
            'password_confirm': 'strongpass123'
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert 'user' in response.data
        assert response.data['user']['email'] == data['email']
        assert 'password' not in response.data['user']  # Never return password!
        assert User.objects.filter(email=data['email']).exists()

    def test_register_user_password_mismatch(self, api_client):
        """
        Test registration fails when passwords don't match

        Requirements:
        - Validate that password and password_confirm match
        - Return 400 Bad Request if they don't match
        - Don't create user in database
        """
        url = reverse('register')
        data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'strongpass123',
            'password_confirm': 'differentpass123'
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not User.objects.filter(email=data['email']).exists()

    def test_register_duplicate_email(self, api_client, test_user):
        """
        Test registration fails with duplicate email

        Requirements:
        - Email should be unique
        - Return 400 Bad Request for duplicate email
        """
        url = reverse('register')
        data = {
            'email': test_user.email,  # Already exists!
            'first_name': 'Another',
            'last_name': 'User',
            'password': 'strongpass123',
            'password_confirm': 'strongpass123'
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogin:
    """
    Test cases for user login

    TODO for Interns:
    Implement the LoginView and LoginSerializer to make these tests pass.
    """

    def test_login_success(self, api_client, test_user):
        """
        Test successful login returns JWT tokens

        Requirements:
        - Accept email and password
        - Validate credentials using Django authenticate
        - Return JWT access and refresh tokens
        - Return user data
        - Return 200 OK status
        """
        url = reverse('login')
        data = {
            'email': 'testuser@example.com',
            'password': 'testpass123'
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert 'tokens' in response.data
        assert 'access' in response.data['tokens']
        assert 'refresh' in response.data['tokens']
        assert 'user' in response.data
        assert response.data['user']['email'] == test_user.email

        # Verify tokens are not empty strings
        assert len(response.data['tokens']['access']) > 20
        assert len(response.data['tokens']['refresh']) > 20

    def test_login_invalid_credentials(self, api_client, test_user):
        """
        Test login fails with wrong password

        Requirements:
        - Return 400 Bad Request for invalid credentials
        - Don't return tokens
        - Return appropriate error message
        """
        url = reverse('login')
        data = {
            'email': 'testuser@example.com',
            'password': 'wrongpassword'
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'tokens' not in response.data

    def test_login_nonexistent_user(self, api_client):
        """
        Test login fails for user that doesn't exist

        Requirements:
        - Return 400 Bad Request
        - Don't return tokens
        """
        url = reverse('login')
        data = {
            'email': 'nonexistent@example.com',
            'password': 'anypassword'
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestMeEndpoint:
    """
    Test cases for /me endpoint

    TODO for Interns:
    Implement the MeView to make these tests pass.
    This tests if JWT authentication is working correctly!
    """

    def test_get_current_user_authenticated(self, authenticated_client, test_user):
        """
        Test authenticated user can access /me endpoint

        Requirements:
        - Require JWT authentication (IsAuthenticated permission)
        - Return current user's data
        - Return 200 OK status
        """
        url = reverse('me')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == test_user.email
        assert response.data['first_name'] == test_user.first_name
        assert 'password' not in response.data

    def test_get_current_user_unauthenticated(self, api_client):
        """
        Test unauthenticated request is rejected

        Requirements:
        - Return 401 Unauthorized without valid JWT token
        - Protect the endpoint with IsAuthenticated permission
        """
        url = reverse('me')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestJWTTokenRefresh:
    """
    Test JWT token refresh functionality

    This is already provided by SimpleJWT!
    These tests verify it's configured correctly.
    """

    def test_refresh_token_success(self, api_client, test_user):
        """
        Test refresh token can generate new access token

        This endpoint is provided by SimpleJWT: POST /api/auth/refresh/
        Your job: Make sure login returns valid refresh tokens!
        """
        # First, login to get tokens
        login_url = reverse('login')
        login_data = {
            'email': 'testuser@example.com',
            'password': 'testpass123'
        }
        login_response = api_client.post(login_url, login_data)
        refresh_token = login_response.data['tokens']['refresh']

        # Now, use refresh token to get new access token
        refresh_url = reverse('token_refresh')
        refresh_data = {'refresh': refresh_token}
        response = api_client.post(refresh_url, refresh_data)

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert len(response.data['access']) > 20


# Bonus Challenge Tests (Optional)
@pytest.mark.django_db
class TestBonusChallenges:
    """
    Extra challenges for interns who finish early!
    """

    def test_register_validates_email_format(self, api_client):
        """
        BONUS: Validate email format

        Add email format validation to your RegisterSerializer
        """
        url = reverse('register')
        data = {
            'email': 'not-an-email',  # Invalid format
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'testpass123',
            'password_confirm': 'testpass123'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_requires_strong_password(self, api_client):
        """
        BONUS: Enforce password strength

        Django has built-in password validators!
        They're already configured in settings.
        """
        url = reverse('register')
        data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': '123',  # Too weak
            'password_confirm': '123'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
