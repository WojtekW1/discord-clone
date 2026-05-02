from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, ProfileForm
from django.contrib.auth import logout
from django.views.decorators.http import require_http_methods

class AppLoginView(LoginView):
    template_name = "auth/login.html"

class AppLogoutView(LogoutView):
    http_method_names = ["get", "post"]
    next_page = "/login/"

def register(request):
    if request.user.is_authenticated:
        return redirect("chat:home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("chat:home")
    return render(request, "auth/register.html", {"form": form})

@login_required
def edit_profile(request):
    profile = request.user.profile
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("chat:home")
    return render(request, "profile/edit.html", {"form": form})

@require_http_methods(["GET", "POST"])
def logout_user(request):
    logout(request)
    return redirect("/login/")