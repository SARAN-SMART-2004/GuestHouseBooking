from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.gmail_login, name='gmail_login'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('logout/', views.logout, name='logout'),
]
