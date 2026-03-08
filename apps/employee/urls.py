from django.urls import path
from .views import EmployeeAPIView, EmployeeDetailAPIView

urlpatterns = [
    path('', EmployeeAPIView.as_view(), name='employee-list-create'),
    path('<int:pk>/', EmployeeDetailAPIView.as_view(), name='employee-detail'),
]