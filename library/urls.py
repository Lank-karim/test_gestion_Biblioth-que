from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    # Page d'accueil
    path('', views.home, name='home'),
    
    # URLs pour les livres
    path('books/', views.book_list, name='book_list'),
    path('books/<int:book_id>/', views.book_detail, name='book_detail'),
    path('library/add/', views.add_book, name='add_book'),
    path('books/<int:book_id>/edit/', views.edit_book, name='edit_book'),
    path('books/<int:book_id>/delete/', views.delete_book, name='delete_book'),
    
    # URLs pour les lecteurs
    path('readers/', views.reader_list, name='reader_list'),
    path('readers/<int:reader_id>/', views.reader_detail, name='reader_detail'),
    path('readers/add/', views.add_reader, name='add_reader'),
    path('readers/<int:reader_id>/edit/', views.edit_reader, name='edit_reader'),
    path('readers/<int:reader_id>/delete/', views.delete_reader, name='delete_reader'),
    
    # URLs pour les réservations
    path('reservations/', views.reservation_list, name='reservation_list'),
    path('reservations/<int:reservation_id>/', views.reservation_detail, name='reservation_detail'),
    path('reservations/create/', views.create_reservation, name='create_reservation'),
    path('reservations/<int:reservation_id>/cancel/', views.cancel_reservation, name='cancel_reservation'),
    
    # URLs AJAX
    path('ajax/reserve/<int:book_id>/', views.quick_reserve, name='quick_reserve'),
    
    # Statistiques
    path('statistics/', views.statistics, name='statistics'),
]
