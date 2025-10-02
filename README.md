# Gestion Bibliothèque - Django

Ce projet est une application Django pour gérer une bibliothèque : livres, lecteurs et réservations.

---

## Prérequis

- Python 3.13+
- Django 5.2+
- virtualenv (ou `venv`)
- SQLite

---

## Installation

1. Cloner le dépôt :

```bash
git clone https://github.com/Lank-karim/test_gestion_Biblioth-que.git
cd test_gestion_Biblioth-que
```
Créer un environnement virtuel et l’activer :

```bash

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```
Installer les dépendances :

```bash

pip install -r requirements.txt
```
Configuration de la base de données

Appliquer les migrations :

```bash

python manage.py makemigrations
python manage.py migrate
```
Créer un superutilisateur pour accéder à l’admin :

```bash

python manage.py createsuperuser
```
Lancer le serveur
```bash

python manage.py runserver
```
Puis ouvrir le navigateur à l’adresse :

```bash

http://127.0.0.1:8000/
```
Acceder à l'interface django admin

```bash

http://127.0.0.1:8000/admin/
```

Lancer les tests
Le projet utilise pytest avec pytest-django :

```bash

pytest
```
Les tests couvrent :

- Modèles (validations, contraintes)

- Vues / CRUD

 - Templates (pages qui se chargent correctement)

URLs principales
API REST :
```

GET /api/books/ → Liste des livres

POST /api/reservations/ → Créer une réservation
```


