# Discord-like Chat (Django + Templates + Bootstrap + Channels)

Spełnia wymagania:
- Rejestracja/login/logout + walidacja unikalności
- Profil (avatar + opis)
- Role: Administrator / Moderator / User (dynamicznie przez Django Groups)
- Kanały tekstowe (tworzenie, dołączanie, historia)
- DM 1:1
- Multimedia: tekst, obraz, audio (upload)
- Moderacja: usuwanie wiadomości (Moderator/Admin), ban (Moderator/Admin)
- Custom 404
- Realtime (WebSocket, Django Channels)
- UI inspirowany Discordem + Bootstrap 5, responsywny

## Lokalnie (dev)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

> Realtime działa lokalnie bez Redis (InMemoryChannelLayer).
> Na produkcji zalecany Redis (Render).

## Render (zalecane)
1. Utwórz repo i wrzuć cały projekt.
2. Na Render: New -> Blueprint (render.yaml) albo Web Service ręcznie.
3. Dodaj Postgres (DATABASE_URL) i Redis (REDIS_URL).
4. Start command:
   `daphne config.asgi:application --bind 0.0.0.0 --port $PORT`
5. Po deploy:
   - wejdź w /admin (superuser) i możesz zarządzać użytkownikami, grupami, banami.

### Wymagane ENV na Render
- DJANGO_SECRET_KEY (Render może wygenerować)
- DJANGO_DEBUG=0
- ALLOWED_HOSTS=.onrender.com (lub Twoja domena)
- CSRF_TRUSTED_ORIGINS=https://*.onrender.com
- DATABASE_URL (z Postgresa)
- REDIS_URL (z Redis)

## Role
- Nowi użytkownicy trafiają do grupy **User** automatycznie.
- Grupy są tworzone automatycznie po migracjach (post_migrate).
- Moderator/Admin: ustaw w /admin -> Users -> Groups.

## Oddanie
- Zip z plikami Django wrzuć na Moodle
- Utwórz plik .txt z linkiem do działającej aplikacji na Render
