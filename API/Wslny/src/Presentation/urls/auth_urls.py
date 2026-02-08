from django.urls import path
from src.Presentation.views.auth_views import RegisterView, LoginView, GoogleLoginView, ProfileView, ChangePasswordView

urlpatterns = [
    path('auth/register', RegisterView.as_view(), name='register'),
    path('auth/login', LoginView.as_view(), name='login'),
    path('auth/google-login', GoogleLoginView.as_view(), name='google-login'),
    path('auth/profile', ProfileView.as_view(), name='profile'),
    path('auth/change-password', ChangePasswordView.as_view(), name='change-password'),
]
