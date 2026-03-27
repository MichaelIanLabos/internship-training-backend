"""
URL configuration for backend project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/employees/', include('apps.employee.urls')),
    path('api/movements/', include('apps.movement.urls')),
]
