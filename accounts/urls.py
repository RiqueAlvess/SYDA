from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("logout/", LogoutView.as_view(next_page='login'), name="logout"),
]