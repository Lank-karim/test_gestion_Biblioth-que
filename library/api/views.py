# library/api/views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from library.models import Book, Reservation
from .serializers import BookSerializer, ReservationSerializer

# GET /api/books/
class BookListAPIView(generics.ListAPIView):
    queryset = Book.objects.all().order_by('title')
    serializer_class = BookSerializer

# POST /api/reservations/
class ReservationCreateAPIView(generics.CreateAPIView):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer

    def create(self, request, *args, **kwargs):
        # On valide que le livre et le lecteur existent
        book_id = request.data.get('book')
        reader_id = request.data.get('reader')

        if not book_id or not reader_id:
            raise ValidationError("Les champs 'book' et 'reader' sont obligatoires.")

        # On laisse la méthode clean() du modèle gérer les règles de réservation
        try:
            return super().create(request, *args, **kwargs)
        except ValidationError as e:
            return Response({"errors": e.message_dict}, status=status.HTTP_400_BAD_REQUEST)
