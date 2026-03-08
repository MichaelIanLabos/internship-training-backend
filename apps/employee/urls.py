from django.urls import path
from .views import EmployeeAPIView, EmployeeDetailAPIView, EmployeeRestoreAPIView

urlpatterns = [
    path('', EmployeeAPIView.as_view(), name='employee-list-create'),
    path('<int:pk>/', EmployeeDetailAPIView.as_view(), name='employee-detail'),
    path('<int:pk>/restore/', EmployeeRestoreAPIView.as_view(), name='employee-restore'),
]