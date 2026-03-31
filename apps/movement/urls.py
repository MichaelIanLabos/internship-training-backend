from django.urls import path
from .views import MovementAPIView, MovementApprovalAPIView, MovementRejectionAPIView

urlpatterns = [
    path('', MovementAPIView.as_view(), name='movement-list-create'),
    path('<int:pk>/approve/', MovementApprovalAPIView.as_view(), name='movement-approve'),
    path('<int:pk>/reject/', MovementRejectionAPIView.as_view(), name='movement-reject'),
]
