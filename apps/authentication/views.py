from rest_framework import status  # noqa: F401
from rest_framework.response import Response  # noqa: F401
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated  # noqa: F401
from rest_framework_simplejwt.tokens import RefreshToken  # noqa: F401
from .serializers import (  # noqa: F401
    LoginSerializer,
    UserSerializer,
    RegisterSerializer,
)


class RegisterView(APIView):
    """
    API endpoint for user registration

    TODO for Interns:
    1. Set permission_classes to [AllowAny] (anyone can register)
    2. Implement POST method:
       - Validate data using RegisterSerializer
       - Save the new user
       - Return user data with 201 status
       - Handle validation errors appropriately

    Expected Request:
    POST /api/auth/register/
    {
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "password": "securepass123",
        "password_confirm": "securepass123"
    }

    Expected Response:
    {
        "user": {
            "id": 1,
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe"
        },
        "message": "User registered successfully. Please login."
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'user': UserSerializer(user).data,
                'message': 'User registered successfully. Please login.',
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    API endpoint for user login - returns JWT tokens

    TODO for Interns:
    1. Set permission_classes to [AllowAny]
    2. Implement POST method:
       - Validate credentials using LoginSerializer
       - Generate JWT tokens for the user
       - Return user data + tokens

    Expected Request:
    POST /api/auth/login/
    {
        "email": "user@example.com",
        "password": "securepass123"
    }

    Expected Response:
    {
        "user": {
            "id": 1,
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe"
        },
        "tokens": {
            "access": "eyJ0eXAiOiJKV1QiLCJhbG...",
            "refresh": "eyJ0eXAiOiJKV1QiLCJhbG..."
        }
    }

    JWT Token Generation:
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
        })


class MeView(APIView):
    """
    API endpoint to get current authenticated user info

    TODO for Interns:
    1. Set permission_classes to [IsAuthenticated]
    2. Implement GET method:
       - Get current user from request.user
       - Serialize user data
       - Return the data

    Expected Request:
    GET /api/auth/me/
    Headers: Authorization: Bearer <access_token>

    Expected Response:
    {
        "id": 1,
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "date_joined": "2024-01-01T00:00:00Z"
    }

    Note: This endpoint tests if JWT authentication is working!
    The user must send a valid access token in the Authorization header.
    """
    permission_classes = []  # TODO: Set to [IsAuthenticated]

    def get(self, request):
        """
        TODO: Implement get current user endpoint
        Steps:
        1. Get user from request.user (DRF provides this automatically)
        2. Serialize with UserSerializer
        3. Return the data

        Hint: request.user is automatically populated by JWT authentication
        """
        # Your code here
        pass
