from django.urls import path
from .views import EmployeeAPIView

urlpatterns = [
    # This matches /api/employees/ when included in the root urls
    path('', EmployeeAPIView.as_view(), name='employee-list-create'),
]