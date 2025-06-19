from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail, mail_admins
from django.conf import settings
import random
import datetime
from .models import UserProfile
from django.utils import timezone
from application.models import UserLog
import pyrebase

config={
    "apiKey": "AIzaSyD-9tSrQWABD1crVgRc6Y-5xq1NrWdp7jE",
    "authDomain": "guest-house-booking-system.firebaseapp.com",
    "projectId": "guest-house-booking-system",
    "storageBucket": "guest-house-booking-system.firebasestorage.app",
    "messagingSenderId": "101010101010",
}
def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp):
    subject = 'Your OTP for Guest House Booking'
    message = f'Your OTP is: {otp}. This OTP is valid for 10 minutes.'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]
    send_mail(subject, message, from_email, recipient_list)

def gmail_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        login_attempts = request.session.get('login_attempts', 0)
        try:
            user = User.objects.get(email=email)
            user = authenticate(username=user.username, password=password)
            if user is not None:
                # Reset login attempts on success
                request.session['login_attempts'] = 0
                # Generate and send OTP
                otp = generate_otp()
                user_profile, created = UserProfile.objects.get_or_create(user=user)
                user_profile.otp = otp
                user_profile.otp_created_at = timezone.now()
                user_profile.save()
                send_otp_email(email, otp)
                request.session['user_id'] = user.id
                request.session['otp_attempts'] = 0
                return redirect('verify_otp')
            else:
                login_attempts += 1
                request.session['login_attempts'] = login_attempts
                if login_attempts >= 3:
                    mail_admins(
                        subject='[ALERT] 3 Failed Login Attempts',
                        message=f'User with email {email} has failed to login 3 times.'
                    )
                    messages.error(request, 'Too many failed login attempts. Admin has been notified.')
                else:
                    messages.error(request, 'Invalid credentials')
        except User.DoesNotExist:
            login_attempts += 1
            request.session['login_attempts'] = login_attempts
            if login_attempts >= 3:
                mail_admins(
                    subject='[ALERT] 3 Failed Login Attempts',
                    message=f'User with email {email} has failed to login 3 times.'
                )
                messages.error(request, 'Too many failed login attempts. Admin has been notified.')
            else:
                messages.error(request, 'User not found')
    return render(request, 'authentication/gmail_login.html')

def verify_otp(request):
    if 'user_id' not in request.session:
        return redirect('gmail_login')
    if request.method == 'POST':
        otp = request.POST.get('otp')
        user_id = request.session['user_id']
        otp_attempts = request.session.get('otp_attempts', 0)
        try:
            user_profile = UserProfile.objects.get(user_id=user_id)
            if user_profile.otp_created_at and (timezone.now() - user_profile.otp_created_at).total_seconds() > 600:
                messages.error(request, 'OTP has expired. Please request a new one.')
                return redirect('gmail_login')
            if user_profile.otp == otp:
                # Reset OTP attempts on success
                request.session['otp_attempts'] = 0
                user = User.objects.get(id=user_id)
                login(request, user)
                user_profile.is_verified = True
                user_profile.otp = None
                user_profile.otp_created_at = None
                user_profile.save()
                UserLog.objects.create(user=user, action='User logged in')
                del request.session['user_id']
                return redirect('home')
            else:
                otp_attempts += 1
                request.session['otp_attempts'] = otp_attempts
                if otp_attempts >= 3:
                    mail_admins(
                        subject='[ALERT] 3 Failed OTP Attempts',
                        message=f'User with id {user_id} has failed OTP verification 3 times.'
                    )
                    messages.error(request, 'Too many failed OTP attempts. Admin has been notified.')
                else:
                    messages.error(request, 'Invalid OTP')
        except UserProfile.DoesNotExist:
            messages.error(request, 'User profile not found')
            return redirect('gmail_login')
    return render(request, 'authentication/verify_otp.html')

def logout(request):
    if request.user.is_authenticated:
        UserLog.objects.create(user=request.user, action='User logged out')
    request.session.flush()
    return redirect('gmail_login')

