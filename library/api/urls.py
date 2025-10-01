from django.urls import path
from .views import BookListAPIView, ReservationCreateAPIView

urlpatterns = [
    path('books/', BookListAPIView.as_view(), name='api_books'),
    path('reservations/', ReservationCreateAPIView.as_view(), name='api_reservations'),
]
