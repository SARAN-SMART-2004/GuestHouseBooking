from .models import GuestHouse

def nav_guesthouses(request):
    return {'nav_guesthouses': GuestHouse.objects.all()} 