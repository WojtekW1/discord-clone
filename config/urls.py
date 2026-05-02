from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.accounts.views import logout_user

from apps.accounts.views import AppLoginView, AppLogoutView, register, edit_profile

handler404 = "config.views.custom_404"

urlpatterns = [
    # ładne URL-e dla użytkownika (discordowe)
    path("logout/", logout_user, name="logout"),
    path("login/", AppLoginView.as_view(), name="login"),
    path("register/", register, name="register"),
    path("profile/", edit_profile, name="profile"),

    # aplikacja
    path("", include("apps.chat.urls")),

    # admin Django (tylko admin/superuser)
    path("admin/", admin.site.urls),

    # (opcjonalnie) zostawiamy stare URL-e, ale user i tak nie będzie ich używał
    path("accounts/", include("apps.accounts.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)