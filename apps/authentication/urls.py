from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, RegisterView, MeView

"""
Authentication URL Configuration

TODO for Interns:
Wire up the authentication endpoints. The URL patterns are already defined,
but make sure your views are properly implemented.

Endpoints to implement:
1. POST /api/auth/register/ - User registration
2. POST /api/auth/login/ - User login (returns JWT tokens)
3. POST /api/auth/refresh/ - Refresh access token (already provided by SimpleJWT)
4. GET /api/auth/me/ - Get current user info (requires authentication)

Testing your endpoints:
- Use Postman, curl, or the Django REST Framework browsable API
- The /api/auth/refresh/ endpoint is provided by SimpleJWT
- Example: POST to /api/auth/refresh/ with {"refresh": "your_refresh_token"}
"""

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Provided by SimpleJWT
    path('me/', MeView.as_view(), name='me'),
]
