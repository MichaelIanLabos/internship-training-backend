from django.urls import path
from .views import MovementAPIView, MovementDetailAPIView, MovementApproveAPIView

urlpatterns = [
    path('', MovementAPIView.as_view(), name='movement-list-create'),
    path('<int:pk>/', MovementDetailAPIView.as_view(), name='movement-detail'),
    path('<int:pk>/approve/', MovementApproveAPIView.as_view(), name='movement-approve'),
]
