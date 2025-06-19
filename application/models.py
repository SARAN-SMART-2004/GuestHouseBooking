from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
import uuid

class GuestHouse(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='guesthouses/')
    address = models.TextField()
    contact_number = models.CharField(max_length=15)
    email = models.EmailField()

    def __str__(self):
        return self.name

class Room(models.Model):
    ROOM_TYPES = [
        ('STANDARD', 'Standard Room'),
        ('SUITE', 'Suite Room'),
    ]

    guest_house = models.ForeignKey(GuestHouse, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(max_length=10)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES)
    number_of_beds = models.IntegerField(validators=[MinValueValidator(1)])
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    description = models.TextField()
    amenities = models.JSONField(default=dict)  # Store amenities as JSON

    def __str__(self):
        return f"{self.guest_house.name} - Room {self.room_number}"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('CONFIRMED', 'Confirmed'),
    ]
    GUEST_TYPE_CHOICES = [
        ('personal', 'Personal'),
        ('guest', 'Guest'),
        ('other', 'Other'),
    ]

    booking_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Available')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    number_of_guests = models.IntegerField(validators=[MinValueValidator(1)], blank=True, null=True)
    special_requests = models.TextField(blank=True)
    address = models.TextField(blank=True, null=True)
    children_count = models.IntegerField(blank=True, null=True)
    proof_document = models.FileField(upload_to='booking_proofs/', blank=True, null=True)
    food_times = models.IntegerField(blank=True, null=True)
    guest_type = models.CharField(max_length=10, choices=GUEST_TYPE_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"Booking {self.booking_id} - {self.room}"

class RoomAvailability(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    date = models.DateField()
    is_available = models.BooleanField(default=True)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('room', 'date')

    def __str__(self):
        return f"{self.room} - {self.date}"

class BookingReport(models.Model):
    guest_house = models.ForeignKey(GuestHouse, on_delete=models.CASCADE)
    month = models.DateField()  # Store first day of month
    total_bookings = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    occupancy_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage

    class Meta:
        unique_together = ('guest_house', 'month')

    def __str__(self):
        return f"{self.guest_house.name} - {self.month.strftime('%B %Y')}"

class UserLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"
