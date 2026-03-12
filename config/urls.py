"""
URL configuration for backend project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.http import JsonResponse


def api_root(request):
    """Root endpoint - confirms API is running."""
    return JsonResponse({'message': 'Backend API is running', 'version': '1.0'})


urlpatterns = [
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.authentication.urls')),
]

if settings.DEBUG:  # pragma: no cover - only used in development
    import debug_toolbar

    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
