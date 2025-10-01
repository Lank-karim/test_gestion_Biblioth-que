from django.contrib import admin
# library/admin.py
from django.contrib import admin
from django.db import models
from django.forms import TextInput, Textarea
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Book, Reader, Reservation


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    """
    Configuration de l'interface d'administration pour le modèle Book.
    """
    list_display = ['title', 'author', 'year', 'availability_status', 'created_at']
    list_filter = ['year', 'created_at', 'author']
    search_fields = ['title', 'author']
    ordering = ['title']
    
    # Regroupement des champs dans le formulaire
    fieldsets = (
        ('Informations du livre', {
            'fields': ('title', 'author', 'year')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    # Personnalisation de l'affichage des widgets
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '40'})},
    }
    
    def availability_status(self, obj):
        """
        Affiche le statut de disponibilité du livre avec des couleurs.
        """
        if obj.is_available():
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Disponible</span>'
            )
        else:
            current_reservation = obj.get_current_reservation()
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Réservé par {}</span>',
                current_reservation.reader.name
            )
    
    availability_status.short_description = "Disponibilité"
    availability_status.admin_order_field = 'reservations'
    
    def get_queryset(self, request):
        """Optimisation des requêtes avec prefetch_related"""
        return super().get_queryset(request).prefetch_related(
            'reservations__reader'
        )
    
    actions = ['make_books_report']
    
    def make_books_report(self, request, queryset):
        """Action personnalisée pour générer un rapport"""
        total = queryset.count()
        available = sum(1 for book in queryset if book.is_available())
        reserved = total - available
        
        self.message_user(
            request,
            f"Rapport: {total} livre(s) sélectionné(s), "
            f"{available} disponible(s), {reserved} réservé(s)."
        )
    
    make_books_report.short_description = "Générer un rapport de disponibilité"


@admin.register(Reader)
class ReaderAdmin(admin.ModelAdmin):
    """
    Configuration de l'interface d'administration pour le modèle Reader.
    """
    list_display = ['name', 'email', 'active_reservations_count', 'total_reservations_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'email']
    ordering = ['name']
    
    fieldsets = (
        ('Informations du lecteur', {
            'fields': ('name', 'email')
        }),
        ('Statistiques', {
            'fields': ('reservations_info',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'reservations_info']
    
    def active_reservations_count(self, obj):
        """Affiche le nombre de réservations actives"""
        count = obj.get_active_reservations().count()
        if count > 0:
            return format_html(
                '<span style="color: orange; font-weight: bold;">{}</span>',
                count
            )
        return count
    
    active_reservations_count.short_description = "Réservations actives"
    
    def total_reservations_count(self, obj):
        """Affiche le nombre total de réservations"""
        return obj.get_reservations_count()
    
    total_reservations_count.short_description = "Total réservations"
    
    def reservations_info(self, obj):
        """Affiche des informations détaillées sur les réservations"""
        active_reservations = obj.get_active_reservations()
        if active_reservations.exists():
            books_list = []
            for reservation in active_reservations:
                book_link = reverse('admin:library_book_change', args=[reservation.book.pk])
                books_list.append(
                    f'<a href="{book_link}" target="_blank">{reservation.book.title}</a>'
                )
            return mark_safe(
                f"<strong>Livres actuellement réservés:</strong><br>" +
                "<br>".join(books_list)
            )
        return "Aucune réservation active"
    
    reservations_info.short_description = "Réservations en cours"
    
    def get_queryset(self, request):
        """Optimisation des requêtes"""
        return super().get_queryset(request).prefetch_related(
            'reservations__book'
        )


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """
    Configuration de l'interface d'administration pour le modèle Reservation.
    """
    list_display = [
        'book_title', 'reader_name', 'reservation_date', 
        'status_display', 'days_since_reservation'
    ]
    list_filter = [
        'is_active', 'reservation_date', 'book__author', 'cancelled_at'
    ]
    search_fields = [
        'book__title', 'book__author', 'reader__name', 'reader__email'
    ]
    ordering = ['-reservation_date']
    
    # Filtres personnalisés
    list_select_related = ['book', 'reader']
    
    fieldsets = (
        ('Réservation', {
            'fields': ('book', 'reader', 'is_active')
        }),
        ('Dates', {
            'fields': ('reservation_date', 'cancelled_at'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['reservation_date']
    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 3, 'cols': 40})},
    }
    
    def book_title(self, obj):
        """Affiche le titre du livre avec un lien"""
        book_link = reverse('admin:library_book_change', args=[obj.book.pk])
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            book_link,
            obj.book.title
        )
    
    book_title.short_description = "Livre"
    book_title.admin_order_field = 'book__title'
    
    def reader_name(self, obj):
        """Affiche le nom du lecteur avec un lien"""
        reader_link = reverse('admin:library_reader_change', args=[obj.reader.pk])
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            reader_link,
            obj.reader.name
        )
    
    reader_name.short_description = "Lecteur"
    reader_name.admin_order_field = 'reader__name'
    
    def status_display(self, obj):
        """Affiche le statut avec des couleurs"""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Active</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Annulée</span>'
            )
    
    status_display.short_description = "Statut"
    status_display.admin_order_field = 'is_active'
    
    def days_since_reservation(self, obj):
        """Calcule le nombre de jours depuis la réservation"""
        from django.utils import timezone
        delta = timezone.now() - obj.reservation_date
        days = delta.days
        
        if obj.is_active:
            if days > 30:  # Plus de 30 jours
                return format_html(
                    '<span style="color: red; font-weight: bold;">{} jours</span>',
                    days
                )
            elif days > 14:  # Plus de 14 jours
                return format_html(
                    '<span style="color: orange; font-weight: bold;">{} jours</span>',
                    days
                )
        
        return f"{days} jours"
    
    days_since_reservation.short_description = "Durée"
    
    actions = ['cancel_reservations', 'reactivate_reservations']
    
    def cancel_reservations(self, request, queryset):
        """Action pour annuler les réservations sélectionnées"""
        cancelled_count = 0
        for reservation in queryset.filter(is_active=True):
            if reservation.cancel():
                cancelled_count += 1
        
        self.message_user(
            request,
            f"{cancelled_count} réservation(s) annulée(s)."
        )
    
    cancel_reservations.short_description = "Annuler les réservations sélectionnées"
    
    def reactivate_reservations(self, request, queryset):
        """Action pour réactiver les réservations sélectionnées"""
        reactivated_count = 0
        errors = []
        
        for reservation in queryset.filter(is_active=False):
            try:
                if reservation.reactivate():
                    reactivated_count += 1
            except Exception as e:
                errors.append(f"{reservation.book.title}: {str(e)}")
        
        message = f"{reactivated_count} réservation(s) réactivée(s)."
        if errors:
            message += f" Erreurs: {'; '.join(errors)}"
        
        self.message_user(request, message)
    
    reactivate_reservations.short_description = "Réactiver les réservations sélectionnées"


# Configuration générale de l'admin
admin.site.site_header = "Administration - Bibliothèque"
admin.site.site_title = "Gestion Bibliothèque"
admin.site.index_title = "Tableau de bord"