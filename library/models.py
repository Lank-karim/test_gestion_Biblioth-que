
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from datetime import datetime


class Book(models.Model):
    """
    Représente un livre dans la bibliothèque.
    """
    title = models.CharField(
        max_length=200,
        verbose_name="Titre",
        help_text="Le titre du livre"
    )
    author = models.CharField(
        max_length=150,
        verbose_name="Auteur",
        help_text="Le nom de l'auteur du livre"
    )
    year = models.PositiveIntegerField(
        verbose_name="Année de publication",
        help_text="L'année où le livre a été publié"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Livre"
        verbose_name_plural = "Livres"
        ordering = ['title']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['author']),
            models.Index(fields=['year']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.author} ({self.year})"
    
    def clean(self):
        """Valide que l'année du livre est réaliste."""
        if self.year > datetime.now().year:
            raise ValidationError({'year': "L'année de publication ne peut pas être dans le futur."})
        if self.year < 1000:
            raise ValidationError({'year': "L'année de publication doit être supérieure à 1000."})
    
    def is_available(self):
        """Retourne True si le livre n'est pas réservé, False sinon."""
        return not self.reservations.filter(is_active=True).exists()
    
    def get_current_reservation(self):
        """Retourne la réservation active du livre, s'il y en a une."""
        return self.reservations.filter(is_active=True).first()

class Reader(models.Model):
    """Représente un lecteur de la bibliothèque."""
    name = models.CharField(
        max_length=100,
        verbose_name="Nom complet",
        help_text="Nom et prénom du lecteur"
    )
    email = models.EmailField(
        unique=True,
        verbose_name="Email",
        help_text="Adresse email du lecteur (unique)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Lecteur"
        verbose_name_plural = "Lecteurs"
        ordering = ['name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    def clean_fields(self, exclude=None):
        """Nettoie les champs AVANT leur validation (important pour l'email)."""
        if self.email:
            self.email = self.email.strip().lower()
        super().clean_fields(exclude=exclude)

    def clean(self):
        """Logique de validation personnalisée (aucune pour l’instant)."""
        super().clean()
    
    def save(self, *args, **kwargs):
        """Assure que l'email est toujours normalisé avant l'enregistrement."""
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)
    
    def get_active_reservations(self):
        """Retourne toutes les réservations actives de ce lecteur."""
        return self.reservations.filter(is_active=True)
    
    def get_reservations_count(self):
        """Retourne le nombre total de réservations du lecteur."""
        return self.reservations.count()


class Reservation(models.Model):
    """
    Représente une réservation d'un livre par un lecteur.
    """
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name="Livre"
    )
    reader = models.ForeignKey(
        Reader,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name="Lecteur"
    )
    reservation_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de réservation"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Réservation active",
        help_text="Indique si la réservation est toujours en cours"
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'annulation"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Informations supplémentaires sur la réservation"
    )
    
    class Meta:
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"
        ordering = ['-reservation_date']
        constraints = [
            # Un livre ne peut avoir qu'une seule réservation active à la fois
            models.UniqueConstraint(
                fields=['book'],
                condition=models.Q(is_active=True),
                name='unique_active_reservation_per_book'
            )
        ]
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['reservation_date']),
        ]
    
    def __str__(self):
        status = "Active" if self.is_active else "Annulée"
        return f"{self.reader.name} - {self.book.title} ({status})"
    
    def clean(self):
        """Validation avant la sauvegarde."""
        if self.pk is None:  # Nouvelle réservation
            # Vérifier que book et reader existent avant de les utiliser
            if not hasattr(self, 'book') or self.book is None:
                # Si book n'est pas défini, Django le validera automatiquement
                return
            
            if not hasattr(self, 'reader') or self.reader is None:
                # Si reader n'est pas défini, Django le validera automatiquement
                return
            
            # Vérifie qu'aucune réservation active n'existe déjà pour ce livre
            if Reservation.objects.filter(book=self.book, is_active=True).exists():
                existing = Reservation.objects.get(book=self.book, is_active=True)
                raise ValidationError({
                    'book': f'Le livre "{self.book.title}" est déjà réservé par {existing.reader.name}.'
                })
            
            # Vérifie que le lecteur n'a pas déjà une réservation active
            if Reservation.objects.filter(reader=self.reader, is_active=True).exists():
                raise ValidationError({
                    'reader': f'Le lecteur "{self.reader.name}" a déjà une réservation en cours.'
                })
    
    def save(self, *args, **kwargs):
        """Valide avant de sauvegarder la réservation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def cancel(self):
        """Annule la réservation si elle est active."""
        if self.is_active:
            self.is_active = False
            self.cancelled_at = datetime.now()
            self.save()
            return True
        return False
    
    def reactivate(self):
        """Réactive la réservation si le livre est disponible."""
        if not self.is_active and self.book.is_available():
            self.is_active = True
            self.cancelled_at = None
            self.save()
            return True
        elif not self.book.is_available():
            raise ValidationError("Le livre est déjà réservé par quelqu'un d'autre.")
        return False
