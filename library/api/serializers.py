from rest_framework import serializers
from library.models import Book, Reservation, Reader

class BookSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'year', 'is_available']

    def get_is_available(self, obj):
        return obj.is_available()

class ReservationSerializer(serializers.ModelSerializer):
    book_title = serializers.ReadOnlyField(source='book.title')
    reader_name = serializers.ReadOnlyField(source='reader.name')

    class Meta:
        model = Reservation
        fields = [
            'id', 'book', 'book_title', 'reader', 'reader_name',
            'reservation_date', 'is_active', 'notes'
        ]
