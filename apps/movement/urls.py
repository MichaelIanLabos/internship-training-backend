from django.urls import path
from .views import MovementAPIView, MovementApprovalAPIView

urlpatterns = [
    path('', MovementAPIView.as_view(), name='movement-list-create'),
    path('<int:pk>/approve/', MovementApprovalAPIView.as_view(), name='movement-approve'),
]
