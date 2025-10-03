from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Book, Reader, Reservation
from .forms import BookForm, ReaderForm, ReservationForm


def home(request):
    """
    Page d'accueil de la bibliothèque avec statistiques globales et dernières activités.
    """
    total_books = Book.objects.count()
    total_readers = Reader.objects.count()
    active_reservations = Reservation.objects.filter(is_active=True).count()
    available_books = total_books - active_reservations

    recent_reservations = Reservation.objects.select_related(
        'book', 'reader'
    ).order_by('-reservation_date')[:5]

    context = {
        'total_books': total_books,
        'total_readers': total_readers,
        'active_reservations': active_reservations,
        'available_books': available_books,
        'recent_reservations': recent_reservations,
    }
    return render(request, 'library/home.html', context)


def book_list(request):
    """
    Affiche la liste des livres avec options de recherche, filtres et pagination.
    """
    books = Book.objects.select_related().prefetch_related('reservations__reader')

    # Recherche par titre ou auteur
    search_query = request.GET.get('search', '').strip()
    if search_query:
        books = books.filter(
            Q(title__icontains=search_query) |
            Q(author__icontains=search_query)
        )

    # Filtre par année
    year_filter = request.GET.get('year')
    if year_filter and year_filter.isdigit():
        books = books.filter(year=int(year_filter))

    # Filtre par disponibilité
    availability_filter = request.GET.get('available')
    if availability_filter == 'true':
        books = books.exclude(reservations__is_active=True)
    elif availability_filter == 'false':
        books = books.filter(reservations__is_active=True)

    # Tri
    sort_by = request.GET.get('sort', 'title')
    if sort_by in ['title', 'author', 'year', '-year']:
        books = books.order_by(sort_by)

    # Pagination
    paginator = Paginator(books, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Liste des années disponibles pour le filtre
    available_years = Book.objects.values_list('year', flat=True).distinct().order_by('-year')

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'year_filter': year_filter,
        'availability_filter': availability_filter,
        'sort_by': sort_by,
        'available_years': available_years,
    }
    return render(request, 'library/book_list.html', context)


def book_detail(request, book_id):
    """
    Détail d'un livre avec son historique de réservations et réservation active.
    """
    book = get_object_or_404(Book, id=book_id)
    reservations_history = book.reservations.select_related('reader').order_by('-reservation_date')
    current_reservation = book.get_current_reservation()

    context = {
        'book': book,
        'current_reservation': current_reservation,
        'reservations_history': reservations_history,
        'is_available': book.is_available(),
    }
    return render(request, 'library/book_detail.html', context)


def reader_list(request):
    """
    Liste des lecteurs avec recherche, tri et pagination.
    """
    readers = Reader.objects.prefetch_related('reservations__book')
    search_query = request.GET.get('search', '').strip()
    if search_query:
        readers = readers.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    sort_by = request.GET.get('sort', 'name')
    if sort_by in ['name', 'email', '-created_at']:
        readers = readers.order_by(sort_by)

    paginator = Paginator(readers, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    return render(request, 'library/reader_list.html', context)


def reader_detail(request, reader_id):
    """
    Détail d'un lecteur avec ses réservations actives et passées.
    """
    reader = get_object_or_404(Reader, id=reader_id)
    all_reservations = reader.reservations.select_related('book').order_by('-reservation_date')
    active_reservations = all_reservations.filter(is_active=True)
    past_reservations = all_reservations.filter(is_active=False)

    context = {
        'reader': reader,
        'active_reservations': active_reservations,
        'past_reservations': past_reservations,
        'total_reservations': all_reservations.count(),
    }
    return render(request, 'library/reader_detail.html', context)


def reservation_list(request):
    """
    Liste des réservations avec recherche, filtre par statut et pagination.
    """
    reservations = Reservation.objects.select_related('book', 'reader')
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        reservations = reservations.filter(is_active=True)
    elif status_filter == 'cancelled':
        reservations = reservations.filter(is_active=False)

    search_query = request.GET.get('search', '').strip()
    if search_query:
        reservations = reservations.filter(
            Q(book__title__icontains=search_query) |
            Q(book__author__icontains=search_query) |
            Q(reader__name__icontains=search_query) |
            Q(reader__email__icontains=search_query)
        )

    sort_by = request.GET.get('sort', '-reservation_date')
    if sort_by in ['-reservation_date', 'reservation_date', 'book__title', 'reader__name']:
        reservations = reservations.order_by(sort_by)

    paginator = Paginator(reservations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'sort_by': sort_by,
    }
    return render(request, 'library/reservation_list.html', context)


def create_reservation(request):
    """
    Crée une nouvelle réservation. Vérifie :
    - que le livre n'est pas déjà réservé
    - que le lecteur n'a pas déjà une réservation active
    """
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            reader = form.cleaned_data['reader']
            if reader.get_active_reservations().exists():
                messages.error(request, f'Le lecteur "{reader.name}" a déjà une réservation en cours.')
            else:
                try:
                    reservation = form.save()
                    messages.success(
                        request,
                        f'Réservation créée avec succès : "{reservation.book.title}" pour {reservation.reader.name}'
                    )
                    return redirect('library:reservation_list')
                except Exception as e:
                    messages.error(request, f'Erreur lors de la création : {str(e)}')
    else:
        form = ReservationForm()

    context = {
        'form': form,
        'available_books': Book.objects.filter(~Q(reservations__is_active=True)).order_by('title'),
    }
    return render(request, 'library/create_reservation.html', context)


def reservation_detail(request, reservation_id):
    """
    Détail d'une réservation spécifique.
    """
    reservation = get_object_or_404(
        Reservation.objects.select_related('book', 'reader'),
        id=reservation_id
    )
    context = {'reservation': reservation}
    return render(request, 'library/reservation_detail.html', context)


@require_http_methods(["POST"])
def cancel_reservation(request, reservation_id):
    """
    Annule une réservation existante (AJAX) et retourne le résultat en JSON.
    """
    reservation = get_object_or_404(Reservation, id=reservation_id)

    if reservation.is_active:
        success = reservation.cancel()
        if success:
            messages.success(request, 'Réservation annulée avec succès.')
            return JsonResponse({'status': 'success', 'message': 'Réservation annulée.'})
        else:
            return JsonResponse({'status': 'error', 'message': "Erreur lors de l'annulation."})
    else:
        return JsonResponse({'status': 'error', 'message': 'Cette réservation est déjà annulée.'})


def add_book(request):
    """
    Ajoute un nouveau livre à la bibliothèque.
    """
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save()
            messages.success(request, f'Livre "{book.title}" ajouté avec succès.')
            return redirect('library:book_list')
    else:
        form = BookForm()

    return render(request, 'library/add_book.html', {'form': form})


def edit_book(request, book_id):
    """
    Modifie les informations d'un livre existant.
    """
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            book = form.save()
            messages.success(request, f'Livre "{book.title}" modifié avec succès.')
            return redirect('library:book_list')
    else:
        form = BookForm(instance=book)

    context = {'form': form, 'book': book}
    return render(request, 'library/edit_book.html', context)


def delete_book(request, book_id):
    """
    Supprime un livre si aucune réservation active n'existe.
    """
    book = get_object_or_404(Book, id=book_id)
    if book.reservations.filter(is_active=True).exists():
        messages.error(request, f'Impossible de supprimer "{book.title}" : il y a des réservations actives.')
        return redirect('library:book_list')

    if request.method == 'POST':
        title = book.title
        book.delete()
        messages.success(request, f'Livre "{title}" supprimé avec succès.')
        return redirect('library:book_list')

    context = {'book': book, 'has_reservations': book.reservations.exists()}
    return render(request, 'library/delete_book.html', context)


def add_reader(request):
    """
    Ajoute un nouveau lecteur.
    """
    if request.method == 'POST':
        form = ReaderForm(request.POST)
        if form.is_valid():
            reader = form.save()
            messages.success(request, f'Lecteur "{reader.name}" ajouté avec succès.')
            return redirect('library:reader_list')
    else:
        form = ReaderForm()
    return render(request, 'library/add_reader.html', {'form': form})


def edit_reader(request, reader_id):
    """
    Modifie les informations d'un lecteur.
    """
    reader = get_object_or_404(Reader, id=reader_id)
    if request.method == 'POST':
        form = ReaderForm(request.POST, instance=reader)
        if form.is_valid():
            reader = form.save()
            messages.success(request, f'Lecteur "{reader.name}" modifié avec succès.')
            return redirect('library:reader_detail', reader_id=reader.id)
    else:
        form = ReaderForm(instance=reader)

    context = {'form': form, 'reader': reader}
    return render(request, 'library/edit_reader.html', context)


def delete_reader(request, reader_id):
    """
    Supprime un lecteur si aucune réservation active n'existe.
    """
    reader = get_object_or_404(Reader, id=reader_id)
    if reader.reservations.filter(is_active=True).exists():
        messages.error(request, f'Impossible de supprimer "{reader.name}" : il y a des réservations actives.')
        return redirect('library:reader_detail', reader_id=reader.id)

    if request.method == 'POST':
        name = reader.name
        reader.delete()
        messages.success(request, f'Lecteur "{name}" supprimé avec succès.')
        return redirect('library:reader_list')

    context = {
        'reader': reader,
        'has_active_reservations': reader.reservations.filter(is_active=True).exists(),
        'total_reservations': reader.reservations.count(),
    }
    return render(request, 'library/delete_reader.html', context)


@csrf_exempt
def quick_reserve(request, book_id):
    """
    Réservation rapide d'un livre via AJAX.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            reader_id = data.get('reader_id')

            book = get_object_or_404(Book, id=book_id)
            reader = get_object_or_404(Reader, id=reader_id)

            # Vérifier la disponibilité du livre
            if not book.is_available():
                return JsonResponse({'status': 'error', 'message': 'Ce livre est déjà réservé.'})

            # Vérifier que le lecteur n'a pas de réservation active
            if reader.get_active_reservations().exists():
                return JsonResponse({'status': 'error', 'message': 'Ce lecteur a déjà une réservation en cours.'})

            # Créer la réservation
            reservation = Reservation.objects.create(book=book, reader=reader)
            return JsonResponse({
                'status': 'success',
                'message': f'Livre réservé avec succès pour {reader.name}',
                'reservation_id': reservation.id
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'})


def statistics(request):
    """
    Affiche des statistiques sur la bibliothèque : livres populaires,
    lecteurs les plus actifs, réservations récentes et par mois.
    """
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models.functions import TruncMonth

    stats = {
        'total_books': Book.objects.count(),
        'total_readers': Reader.objects.count(),
        'total_reservations': Reservation.objects.count(),
        'active_reservations': Reservation.objects.filter(is_active=True).count(),
    }

    popular_books = Book.objects.annotate(reservation_count=Count('reservations'))\
        .filter(reservation_count__gt=0).order_by('-reservation_count')[:10]

    active_readers = Reader.objects.annotate(reservation_count=Count('reservations'))\
        .filter(reservation_count__gt=0).order_by('-reservation_count')[:10]

    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_reservations = Reservation.objects.filter(reservation_date__gte=thirty_days_ago).count()

    monthly_reservations = Reservation.objects.filter(
        reservation_date__gte=timezone.now() - timedelta(days=180)
    ).annotate(
        month=TruncMonth('reservation_date')
    ).values('month').annotate(count=Count('id')).order_by('month')

    context = {
        'stats': stats,
        'popular_books': popular_books,
        'active_readers': active_readers,
        'recent_reservations': recent_reservations,
        'monthly_reservations': monthly_reservations,
    }
    return render(request, 'library/statistics.html', context)

