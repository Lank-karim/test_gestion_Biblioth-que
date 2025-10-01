# library/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from datetime import datetime
from .models import Book, Reader, Reservation


class BookForm(forms.ModelForm):
    """
    Formulaire pour créer et modifier un livre.
    """
    
    class Meta:
        model = Book
        fields = ['title', 'author', 'year']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre du livre',
                'maxlength': 200
            }),
            'author': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de l\'auteur',
                'maxlength': 150
            }),
            'year': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Année de publication',
                'min': 1000,
                'max': datetime.now().year
            }),
        }
        labels = {
            'title': 'Titre',
            'author': 'Auteur',
            'year': 'Année de publication',
        }
        help_texts = {
            'title': 'Le titre complet du livre',
            'author': 'Le nom complet de l\'auteur principal',
            'year': 'L\'année de première publication',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Marquer tous les champs comme requis
        for field in self.fields.values():
            field.required = True
    
    def clean_title(self):
        """Validation personnalisée du titre"""
        title = self.cleaned_data.get('title')
        if title:
            title = title.strip()
            if len(title) < 2:
                raise ValidationError('Le titre doit contenir au moins 2 caractères.')
        return title
    
    def clean_author(self):
        """Validation personnalisée de l'auteur"""
        author = self.cleaned_data.get('author')
        if author:
            author = author.strip()
            if len(author) < 2:
                raise ValidationError('Le nom de l\'auteur doit contenir au moins 2 caractères.')
        return author
    
    def clean_year(self):
        """Validation personnalisée de l'année"""
        year = self.cleaned_data.get('year')
        if year:
            current_year = datetime.now().year
            if year > current_year:
                raise ValidationError('L\'année ne peut pas être dans le futur.')
            if year < 1000:
                raise ValidationError('L\'année doit être supérieure à 1000.')
        return year


class ReaderForm(forms.ModelForm):
    """
    Formulaire pour créer et modifier un lecteur.
    """
    
    class Meta:
        model = Reader
        fields = ['name', 'email']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom complet du lecteur',
                'maxlength': 100
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'adresse@email.com',
            }),
        }
        labels = {
            'name': 'Nom complet',
            'email': 'Adresse email',
        }
        help_texts = {
            'name': 'Le nom et prénom du lecteur',
            'email': 'Une adresse email valide et unique',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Marquer tous les champs comme requis
        for field in self.fields.values():
            field.required = True
    
    def clean_name(self):
        """Validation personnalisée du nom"""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if len(name) < 2:
                raise ValidationError('Le nom doit contenir au moins 2 caractères.')
            # Vérifier qu'il n'y a pas que des chiffres
            if name.isdigit():
                raise ValidationError('Le nom ne peut pas contenir uniquement des chiffres.')
        return name
    
    def clean_email(self):
        """Validation personnalisée de l'email"""
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
            
            # Vérifier l'unicité seulement si c'est un nouveau lecteur ou si l'email a changé
            if self.instance.pk is None or self.instance.email != email:
                if Reader.objects.filter(email=email).exists():
                    raise ValidationError('Cette adresse email est déjà utilisée par un autre lecteur.')
        
        return email


class ReservationForm(forms.ModelForm):
    """
    Formulaire pour créer une réservation.
    """
    
    class Meta:
        model = Reservation
        fields = ['book', 'reader', 'notes']
        widgets = {
            'book': forms.Select(attrs={
                'class': 'form-control',
            }),
            'reader': forms.Select(attrs={
                'class': 'form-control',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes supplémentaires (optionnel)...'
            }),
        }
        labels = {
            'book': 'Livre',
            'reader': 'Lecteur',
            'notes': 'Notes',
        }
        help_texts = {
            'book': 'Sélectionnez le livre à réserver',
            'reader': 'Sélectionnez le lecteur',
            'notes': 'Notes supplémentaires sur cette réservation',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Limiter les livres aux livres disponibles uniquement
        self.fields['book'].queryset = Book.objects.filter(
            ~Q(reservations__is_active=True)
        ).order_by('title')
        
        # Ordonner les lecteurs par nom
        self.fields['reader'].queryset = Reader.objects.all().order_by('name')
        
        # Le champ notes n'est pas requis
        self.fields['notes'].required = False
        
        # Ajouter des classes CSS Bootstrap
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
    def clean(self):
        """Validation globale du formulaire"""
        cleaned_data = super().clean()
        book = cleaned_data.get('book')
        reader = cleaned_data.get('reader')
        
        if book and reader:
            # Vérifier que le livre est toujours disponible
            if not book.is_available():
                current_reservation = book.get_current_reservation()
                raise ValidationError(
                    f'Le livre "{book.title}" est déjà réservé par {current_reservation.reader.name}.'
                )
            
            # Vérifier que le lecteur n'a pas trop de réservations actives
            active_reservations_count = reader.get_active_reservations().count()
            MAX_ACTIVE_RESERVATIONS = 5  # Limite configurable
            
            if active_reservations_count >= MAX_ACTIVE_RESERVATIONS:
                raise ValidationError(
                    f'Le lecteur {reader.name} a déjà {active_reservations_count} réservations actives. '
                    f'Limite maximale : {MAX_ACTIVE_RESERVATIONS}.'
                )
        
        return cleaned_data


class BookSearchForm(forms.Form):
    """
    Formulaire de recherche pour les livres.
    """
    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher par titre ou auteur...',
        }),
        label='Recherche'
    )
    
    year = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Année'
    )
    
    available = forms.ChoiceField(
        choices=[
            ('', 'Tous les livres'),
            ('true', 'Disponibles uniquement'),
            ('false', 'Réservés uniquement'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Disponibilité'
    )
    
    sort = forms.ChoiceField(
        choices=[
            ('title', 'Titre (A-Z)'),
            ('author', 'Auteur (A-Z)'),
            ('year', 'Année (ancienne en premier)'),
            ('-year', 'Année (récente en premier)'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Trier par',
        initial='title'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Générer les choix d'années dynamiquement
        years = Book.objects.values_list('year', flat=True).distinct().order_by('-year')
        year_choices = [('', 'Toutes les années')]
        year_choices.extend([(year, str(year)) for year in years])
        self.fields['year'].choices = year_choices


class ReaderSearchForm(forms.Form):
    """
    Formulaire de recherche pour les lecteurs.
    """
    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher par nom ou email...',
        }),
        label='Recherche'
    )
    
    sort = forms.ChoiceField(
        choices=[
            ('name', 'Nom (A-Z)'),
            ('email', 'Email (A-Z)'),
            ('-created_at', 'Plus récents en premier'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Trier par',
        initial='name'
    )


class ReservationSearchForm(forms.Form):
    """
    Formulaire de recherche pour les réservations.
    """
    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher par livre, auteur, lecteur...',
        }),
        label='Recherche'
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'Toutes les réservations'),
            ('active', 'Actives uniquement'),
            ('cancelled', 'Annulées uniquement'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Statut'
    )
    
    sort = forms.ChoiceField(
        choices=[
            ('-reservation_date', 'Plus récentes en premier'),
            ('reservation_date', 'Plus anciennes en premier'),
            ('book__title', 'Titre du livre (A-Z)'),
            ('reader__name', 'Nom du lecteur (A-Z)'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Trier par',
        initial='-reservation_date'
    )


class QuickReservationForm(forms.Form):
    """
    Formulaire simplifié pour réservation rapide (AJAX).
    """
    reader = forms.ModelChoiceField(
        queryset=Reader.objects.all().order_by('name'),
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Lecteur',
        empty_label='Sélectionner un lecteur...'
    )
    
    def __init__(self, book=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.book = book
        
        if book and not book.is_available():
            # Si le livre n'est pas disponible, désactiver le formulaire
            self.fields['reader'].disabled = True
            self.fields['reader'].help_text = 'Ce livre est déjà réservé.'
    
    def clean(self):
        """Validation du formulaire"""
        cleaned_data = super().clean()
        reader = cleaned_data.get('reader')
        
        if self.book and reader:
            # Vérifier que le livre est toujours disponible
            if not self.book.is_available():
                raise ValidationError('Ce livre n\'est plus disponible.')
            
            # Vérifier les limites de réservation du lecteur
            active_count = reader.get_active_reservations().count()
            if active_count >= 5:  # Limite configurable
                raise ValidationError(
                    f'{reader.name} a déjà {active_count} réservations actives.'
                )
        
        return cleaned_data