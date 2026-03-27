from django.urls import path
from .views import MovementAPIView

urlpatterns = [
    path('', MovementAPIView.as_view(), name='movement-list-create'),
]
