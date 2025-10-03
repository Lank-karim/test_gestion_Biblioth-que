import pytest
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Book, Reader, Reservation

pytestmark = pytest.mark.django_db


# ---------------------------
# Fixtures helpers / Données factices
# ---------------------------
@pytest.fixture
def sample_book():
    # Création d'un livre exemple
    return Book.objects.create(title="Test Book", author="Author X", year=2000)


@pytest.fixture
def sample_reader():
    # Création d'un lecteur exemple
    return Reader.objects.create(name="John Tester", email=" JOHN.TESTER@EXAMPLE.COM ")


# ---------------------------
# TESTS DU MODÈLE
# ---------------------------
def test_book_clean_year_future_raises():
    # Vérifie que la validation échoue si l'année de publication est dans le futur
    future_year = timezone.now().year + 5
    b = Book(title="Future", author="Time Traveller", year=future_year)
    with pytest.raises(ValidationError) as exc:
        b.full_clean()
    assert "L'année de publication ne peut pas être dans le futur." in str(exc.value)


def test_book_clean_year_too_small_raises():
    # Vérifie que la validation échoue si l'année de publication est trop ancienne (< 1000)
    b = Book(title="Ancient", author="Old Author", year=999)
    with pytest.raises(ValidationError):
        b.full_clean()


def test_reader_clean_email_normalizes(sample_reader):
    # Vérifie que la méthode clean() normalise correctement l'email (minuscules et suppression des espaces)
    r = Reader(name="Temp", email="  MixedCase@Email.COM ")
    # full_clean() appelle clean() automatiquement
    r.full_clean()
    assert r.email == "mixedcase@email.com"


def test_reservation_model_enforces_single_active_per_book(sample_book, sample_reader):
    # Création d'une première réservation active
    r1 = Reservation.objects.create(book=sample_book, reader=sample_reader)
    assert r1.is_active is True
    # Tentative de créer une deuxième réservation active sur le même livre -> doit lever ValidationError
    r2 = Reservation(book=sample_book, reader=Reader.objects.create(name="Other", email="other@example.com"))
    with pytest.raises(ValidationError):
        # La méthode save() appelle full_clean() dans le modèle, donc l'enregistrement doit échouer
        r2.save()


def test_reservation_model_prevents_reader_having_two_active_reservations(sample_book, sample_reader):
    # Création d'un autre livre
    b2 = Book.objects.create(title="Book 2", author="A", year=1999)
    # Première réservation du lecteur sur le premier livre
    Reservation.objects.create(book=sample_book, reader=sample_reader)
    # Tentative de réservation pour le même lecteur sur un livre différent -> doit lever ValidationError
    r = Reservation(book=b2, reader=sample_reader)
    with pytest.raises(ValidationError):
        r.save()


# ---------------------------
# TESTS DES VUES / CRUD / TEMPLATES
# ---------------------------
def test_book_list_page_loads(client):
    # Vérifie que la page de liste des livres se charge correctement
    url = reverse('library:book_list')
    resp = client.get(url)
    assert resp.status_code == 200


def test_add_edit_delete_book_views(client):
    # -------------------
    # AJOUT
    # -------------------
    add_url = reverse('library:add_book')
    data = {'title': 'Created Book', 'author': 'Auth', 'year': 2010}
    resp = client.post(add_url, data)
    # Vérifie la redirection vers la liste des livres
    assert resp.status_code in (302, 303)
    assert Book.objects.filter(title='Created Book').exists()
    book = Book.objects.get(title='Created Book')

    # -------------------
    # MODIFICATION
    # -------------------
    edit_url = reverse('library:edit_book', args=[book.id])
    data_edit = {'title': 'Edited Book', 'author': 'Auth Edited', 'year': 2011}
    resp = client.post(edit_url, data_edit)
    assert resp.status_code in (302, 303)
    book.refresh_from_db()
    assert book.title == 'Edited Book'
    assert book.year == 2011

    # -------------------
    # SUPPRESSION
    # -------------------
    delete_url = reverse('library:delete_book', args=[book.id])
    # Vérifie qu'aucune réservation active ne bloque la suppression
    resp = client.post(delete_url, {})
    assert resp.status_code in (302, 303)
    assert not Book.objects.filter(id=book.id).exists()


def test_reader_crud_views(client):
    # -------------------
    # AJOUT
    # -------------------
    add_url = reverse('library:add_reader')
    data = {'name': 'Alice', 'email': 'alice@example.com'}
    resp = client.post(add_url, data)
    assert resp.status_code in (302, 303)
    assert Reader.objects.filter(email='alice@example.com').exists()
    reader = Reader.objects.get(email='alice@example.com')

    # -------------------
    # MODIFICATION
    # -------------------
    edit_url = reverse('library:edit_reader', args=[reader.id])
    data_edit = {'name': 'Alice Edited', 'email': 'alice2@example.com'}
    resp = client.post(edit_url, data_edit)
    assert resp.status_code in (302, 303)
    reader.refresh_from_db()
    assert reader.name == 'Alice Edited'
    assert reader.email == 'alice2@example.com'

    # -------------------
    # SUPPRESSION
    # -------------------
    delete_url = reverse('library:delete_reader', args=[reader.id])
    resp = client.post(delete_url, {})
    assert resp.status_code in (302, 303)
    assert not Reader.objects.filter(id=reader.id).exists()


def test_create_reservation_view_and_business_rules(client):
    # Création d'un livre et d'un lecteur
    b = Book.objects.create(title="Res Book", author="A", year=2005)
    r = Reader.objects.create(name="Res Reader", email="res@example.com")

    create_url = reverse('library:create_reservation')
    data = {'book': b.id, 'reader': r.id, 'notes': 'Test reserve'}

    # Création de la réservation
    resp = client.post(create_url, data)
    # Doit rediriger vers la liste des réservations
    assert resp.status_code in (302, 303)
    assert Reservation.objects.filter(book=b, reader=r, is_active=True).exists()

    # Deuxième tentative : ne doit pas créer une autre réservation active pour le même livre
    resp2 = client.post(create_url, {'book': b.id, 'reader': Reader.objects.create(name="X", email="x@example.com").id})
    # La vue gère le cas et re-render la page avec une erreur, donc status 200
    assert resp2.status_code == 200
    assert Reservation.objects.filter(book=b, is_active=True).count() == 1


def test_pages_render_templates(client, sample_book, sample_reader):
    # Teste que plusieurs pages importantes retournent 200 ou 302
    urls = [
        reverse('library:home'),
        reverse('library:book_list'),
        reverse('library:reader_list'),
        reverse('library:add_book'),
        reverse('library:add_reader'),
        reverse('library:reservation_list'),
        reverse('library:create_reservation'),
    ]
    for url in urls:
        resp = client.get(url)
        # Certaines pages peuvent rediriger si des permissions sont requises
        # Ici on vérifie juste qu'elles ne renvoient pas 500
        assert resp.status_code in (200, 302)
