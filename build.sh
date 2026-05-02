#!/usr/bin/env bash
set -o errexit

python manage.py migrate
python manage.py collectstatic --noinput

# create superuser if it doesn't exist (Render Free - no shell)
python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()
u = os.environ.get('DJANGO_SUPERUSER_USERNAME')
e = os.environ.get('DJANGO_SUPERUSER_EMAIL')
p = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
if u and e and p and not User.objects.filter(username=u).exists():
    User.objects.create_superuser(username=u, email=e, password=p)
    print('Created superuser:', u)
else:
    print('Superuser exists or env missing')
"