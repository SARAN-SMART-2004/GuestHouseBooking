from django.contrib import admin
from .models import GuestHouse, Room, Booking, RoomAvailability, BookingReport, UserLog

admin.site.register(GuestHouse)
admin.site.register(Room)
admin.site.register(Booking)
admin.site.register(RoomAvailability)
admin.site.register(BookingReport)
admin.site.register(UserLog)
