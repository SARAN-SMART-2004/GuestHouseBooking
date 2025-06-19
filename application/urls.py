from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('guest-house/<int:guest_house_id>/', views.guest_house_detail, name='guest_house_detail'),
    path('check-availability/', views.check_availability, name='check_availability'),
    path('book-room/', views.book_room, name='book_room'),
    path('booking-report/', views.booking_report, name='booking_report'),
    path('add-guesthouse/', views.add_guesthouse, name='add_guesthouse'),
    path('add-room/', views.add_room, name='add_room'),
    path('room-booking-report/', views.room_booking_report, name='room_booking_report'),
    path('download-booking-history/', views.download_booking_history, name='download_booking_history'),
    path('download-booking-history/pdf/', views.download_booking_history_pdf, name='download_booking_history_pdf'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('edit-guesthouse/', views.edit_guesthouse, name='edit_guesthouse'),
    path('edit-guesthouse/<int:guest_house_id>/', views.edit_guesthouse, name='edit_guesthouse_form'),
    path('edit-room/', views.edit_room, name='edit_room'),
    path('edit-room/<int:room_id>/', views.edit_room, name='edit_room_form'),
    path('guesthouse-list/', views.guesthouse_list, name='guesthouse_list'),
    path('room-list/', views.room_list, name='room_list'),
    path('today-reserved-rooms/<int:guest_house_id>/', views.today_reserved_rooms, name='today_reserved_rooms'),
    path('logs/', views.logs, name='logs'),
]
