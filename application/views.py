from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta, date
from .models import GuestHouse, Room, Booking, RoomAvailability, BookingReport, UserLog
import json
from django.http import JsonResponse, HttpResponse
from django.core.serializers import serialize
from django.contrib.admin.views.decorators import staff_member_required
from django import forms
from django.template.loader import render_to_string
import io
from xhtml2pdf import pisa
from django.contrib.auth.models import User
from django.contrib.auth.models import User

def log_user_action(user, action):
    from .models import UserLog
    if user.is_authenticated:
        UserLog.objects.create(user=user, action=action)

@login_required
def home(request):
    guest_houses = GuestHouse.objects.all()
    guest_houses_data = []
    for gh in guest_houses:
        rooms = Room.objects.filter(guest_house=gh)
        room_count = rooms.count()
        available_rooms_count = rooms.filter(is_available=True).count()
        # Booked rooms: rooms with at least one CONFIRMED booking whose check-in/check-out includes today
        today = date.today()
        booked_rooms_count = Booking.objects.filter(
            room__guest_house=gh,
            status="CONFIRMED",
            check_in_date__lte=today,
            check_out_date__gte=today
        ).count()
        guest_houses_data.append({
            'id': gh.id,
            'name': gh.name,
            'description': gh.description,
            'image': gh.image,
            'room_count': room_count,
            'address': gh.address,
            'available_rooms_count': available_rooms_count,
            'booked_rooms_count': booked_rooms_count,
        })
    log_user_action(request.user, 'Viewed home page')
    return render(request, 'application/home.html', {'guest_houses': guest_houses_data})

@login_required
def guest_house_detail(request, guest_house_id):
    guest_house = get_object_or_404(GuestHouse, id=guest_house_id)
    rooms = Room.objects.filter(guest_house=guest_house)
    today = date.today()
    total_rooms = rooms.count()
    available_rooms = rooms.filter(is_available=True)
    available_rooms_count = available_rooms.count()
    booked_rooms = Booking.objects.filter(
        room__guest_house=guest_house,
        status="CONFIRMED",
        check_in_date__lte=today,
        check_out_date__gte=today
    )
    booked_rooms_count = booked_rooms.count()
    # For room list, get booking status for today
    room_status_map = {room.id: 'Available' for room in rooms}
    for booking in booked_rooms:
        room_status_map[booking.room.id] = 'Booked'
    log_user_action(request.user, f'Viewed guest house detail for guest house {guest_house_id}')
    return render(request, 'application/guest_house_detail.html', {
        'guest_house': guest_house,
        'rooms': rooms,
        'total_rooms': total_rooms,
        'available_rooms_count': available_rooms_count,
        'booked_rooms_count': booked_rooms_count,
        'room_status_map': room_status_map,
        'today': today,
        'booked_rooms': booked_rooms,
    })

@login_required
def check_availability(request):
    log_user_action(request.user, f'Checked availability for guest house {request.GET.get("guest_house_id", "N/A")}')
    if request.method == 'POST':
        data = json.loads(request.body)
        check_in = datetime.strptime(data['check_in'], '%Y-%m-%d').date()
        check_out = datetime.strptime(data['check_out'], '%Y-%m-%d').date()
        guest_house_id = data['guest_house_id']
        rooms = Room.objects.filter(guest_house_id=guest_house_id, is_available=True)
        available_rooms = []
        for room in rooms:
            is_available = True
            current_date = check_in
            while current_date <= check_out:
                if RoomAvailability.objects.filter(room=room, date=current_date, is_available=False).exists():
                    is_available = False
                    break
                current_date += timedelta(days=1)
            if is_available:
                available_rooms.append({
                    'id': room.id,
                    'room_number': room.room_number,
                    'room_type': room.room_type,
                    'number_of_beds': room.number_of_beds,
                    'price_per_night': float(room.price_per_night),
                    'description': room.description,
                    'amenities': room.amenities
                })
        return JsonResponse({'available_rooms': available_rooms})

@login_required
def book_room(request):
    log_user_action(request.user, f'Attempted to book room {request.GET.get("room_id", "N/A")}')
    if request.method == 'POST':
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            files = None
        else:
            data = request.POST
            files = request.FILES
        room_id = data.get('room_id')
        check_in = data.get('check_in')
        check_out = data.get('check_out')
        status="CONFIRMED"
        number_of_guests = data.get('number_of_guests')
        special_requests = data.get('special_requests', '')
        address = data.get('address', '')
        children_count = data.get('children_count')
        food_times = data.get('food_times')
        guest_type = data.get('guest_type')
        proof_document = files['proof_document'] if files and 'proof_document' in files else None

        check_in = datetime.strptime(check_in, '%Y-%m-%d').date() if check_in else None
        check_out = datetime.strptime(check_out, '%Y-%m-%d').date() if check_out else None
        room = get_object_or_404(Room, id=room_id)
        nights = (check_out - check_in).days if check_in and check_out else 0
        total_price = room.price_per_night * nights if nights > 0 else 0

        booking = Booking.objects.create(
            user=request.user,
            room=room,
            check_in_date=check_in,
            check_out_date=check_out,
            number_of_guests=number_of_guests or None,
            special_requests=special_requests,
            status=status,
            total_price=total_price,
            address=address,
            children_count=children_count or None,
            proof_document=proof_document,
            food_times=food_times or None,
            guest_type=guest_type or None,
        )

        # Update room availability
        if check_in and check_out:
            current_date = check_in
            while current_date <= check_out:
                RoomAvailability.objects.create(
                    room=room,
                    date=current_date,
                    is_available=False,
                    booking=booking
                )
                current_date += timedelta(days=1)

        # Update booking report
        if check_in:
            month_start = check_in.replace(day=1)
            report, created = BookingReport.objects.get_or_create(
                guest_house=room.guest_house,
                month=month_start
            )
            report.total_bookings += 1
            report.total_revenue += total_price
            report.save()

        return JsonResponse({
            'success': True,
            'booking_id': str(booking.booking_id)
        })

@login_required
def booking_report(request):
    if not request.user.is_staff:
        messages.error(request, 'Access denied')
        return redirect('home')

    # Get monthly reports for all guest houses
    reports = BookingReport.objects.all().order_by('month')
    
    # Prepare data for charts
    guest_houses = GuestHouse.objects.all()
    months = sorted(set(report.month for report in reports))
    
    booking_data = {
        'labels': [month.strftime('%B %Y') for month in months],
        'datasets': []
    }
    
    revenue_data = {
        'labels': [month.strftime('%B %Y') for month in months],
        'datasets': []
    }
    
    for guest_house in guest_houses:
        house_reports = reports.filter(guest_house=guest_house)
        
        booking_data['datasets'].append({
            'label': guest_house.name,
            'data': [report.total_bookings for report in house_reports]
        })
        
        revenue_data['datasets'].append({
            'label': guest_house.name,
            'data': [float(report.total_revenue) for report in house_reports]
        })

    log_user_action(request.user, 'Viewed booking report')
    return render(request, 'application/booking_report.html', {
        'reports': reports,
        'booking_data': json.dumps(booking_data),
        'revenue_data': json.dumps(revenue_data)
    })

@login_required
@staff_member_required
def add_guesthouse(request):
    if request.method == 'POST':
        form = GuestHouseForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Guest house added successfully!')
            return redirect('home')
    else:
        form = GuestHouseForm()
    log_user_action(request.user, 'Added new guest house')
    return render(request, 'application/add_guesthouse.html', {'form': form})

@login_required
@staff_member_required
def add_room(request):
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Room added successfully!')
            return redirect('home')
    else:
        form = RoomForm()
    log_user_action(request.user, 'Added new room')
    return render(request, 'application/add_room.html', {'form': form})

from calendar import monthrange

@login_required
def room_booking_report(request):
    import calendar
    from datetime import date
    # Get filter values from GET params
    month = int(request.GET.get('month', date.today().month))
    year = int(request.GET.get('year', date.today().year))
    # Get all rooms
    rooms = Room.objects.all().select_related('guest_house')
    # Get bookings for the selected month/year
    bookings = Booking.objects.filter(
        check_in_date__year=year,
        check_in_date__month=month
    ).select_related('room', 'room__guest_house', 'user')
    # For filter dropdowns
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]
    years = list(range(date.today().year - 5, date.today().year + 2))
    log_user_action(request.user, f'Viewed room booking report for month {month} and year {year}')
    return render(request, 'application/room_booking_report.html', {
        'rooms': rooms,
        'bookings': bookings,
        'selected_month': month,
        'selected_year': year,
        'months': months,
        'years': years,
    })

@login_required
def download_booking_history(request):
    log_user_action(request.user, 'Accessed download booking history page')
    from datetime import date
    bookings = []
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    if from_date and to_date:
        bookings = Booking.objects.filter(
            check_in_date__gte=from_date,
            check_out_date__lte=to_date
        ).select_related('room', 'room__guest_house', 'user')
    return render(request, 'application/download_booking_history.html', {
        'bookings': bookings,
        'from_date': from_date,
        'to_date': to_date,
    })

@login_required
def download_booking_history_pdf(request):
    log_user_action(request.user, 'Downloaded booking history PDF')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    bookings = []
    if from_date and to_date:
        bookings = Booking.objects.filter(
            check_in_date__gte=from_date,
            check_out_date__lte=to_date
        ).select_related('room', 'room__guest_house', 'user')
    html = render_to_string('application/download_booking_history_pdf.html', {
        'bookings': bookings,
        'from_date': from_date,
        'to_date': to_date,
    })
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="booking_history.pdf"'
    pisa.CreatePDF(io.StringIO(html), dest=response)
    return response

@login_required
def dashboard(request):
    log_user_action(request.user, 'Viewed dashboard')
    return render(request, 'application/dashboard.html')

@login_required
def edit_guesthouse(request, guest_house_id=None):
    from .models import GuestHouse
    if guest_house_id:
        guesthouse = GuestHouse.objects.get(id=guest_house_id)
        if request.method == 'POST':
            form = GuestHouseForm(request.POST, request.FILES, instance=guesthouse)
            if form.is_valid():
                form.save()
                messages.success(request, 'Guesthouse updated successfully!')
                return redirect('edit_guesthouse')
        else:
            form = GuestHouseForm(instance=guesthouse)
        log_user_action(request.user, f'Edited guest house {guest_house_id}')
        return render(request, 'application/edit_guesthouse_form.html', {'form': form, 'guesthouse': guesthouse})
    else:
        guesthouses = GuestHouse.objects.all()
        return render(request, 'application/edit_guesthouse_list.html', {'guesthouses': guesthouses})

@login_required
@staff_member_required
def edit_room(request, room_id=None):
    from .models import Room
    if room_id:
        room = Room.objects.get(id=room_id)
        if request.method == 'POST':
            form = RoomForm(request.POST, instance=room)
            if form.is_valid():
                form.save()
                messages.success(request, 'Room updated successfully!')
                return redirect('edit_room')
        else:
            form = RoomForm(instance=room)
        log_user_action(request.user, f'Edited room {room_id}')
        return render(request, 'application/edit_room_form.html', {'form': form, 'room': room})
    else:
        rooms = Room.objects.all()
        return render(request, 'application/edit_room_list.html', {'rooms': rooms})

# Add the form classes back here:
class GuestHouseForm(forms.ModelForm):
    class Meta:
        model = GuestHouse
        fields = ['name', 'description', 'image', 'address', 'contact_number', 'email']

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['guest_house', 'room_number', 'room_type', 'number_of_beds', 'price_per_night', 'description', 'amenities']

@login_required
def guesthouse_list(request):
    from .models import GuestHouse
    guesthouses = GuestHouse.objects.all()
    log_user_action(request.user, 'Viewed guest house list')
    return render(request, 'application/guesthouse_list.html', {'guesthouses': guesthouses})

@login_required
def room_list(request):
    from .models import Room, GuestHouse
    rooms = Room.objects.all()
    guesthouses = GuestHouse.objects.all()
    room_types = Room.objects.values_list('room_type', flat=True).distinct()

    guesthouse_id = request.GET.get('guesthouse')
    room_type = request.GET.get('room_type')
    search = request.GET.get('search')

    if guesthouse_id:
        rooms = rooms.filter(guest_house_id=guesthouse_id)
    if room_type:
        rooms = rooms.filter(room_type=room_type)
    if search:
        rooms = rooms.filter(
            Q(room_number__icontains=search) |
            Q(guest_house__name__icontains=search)
        )

    return render(request, 'application/room_list.html', {
        'rooms': rooms,
        'guesthouses': guesthouses,
        'room_types': room_types,
        'selected_guesthouse': guesthouse_id,
        'selected_room_type': room_type,
        'search': search,
    })

@login_required
def today_reserved_rooms(request, guest_house_id):
    log_user_action(request.user, f'Viewed today reserved rooms for guest house {guest_house_id}')
    from .models import Room, Booking, GuestHouse
    guest_house = GuestHouse.objects.get(id=guest_house_id)
    today = date.today()
    bookings = Booking.objects.filter(
        room__guest_house=guest_house,
        check_in_date__lte=today,
        check_out_date__gte=today
    ).select_related('room', 'user')
    return render(request, 'application/today_reserved_rooms.html', {
        'guest_house': guest_house,
        'bookings': bookings,
        'today': today,
    })

@staff_member_required
@login_required
def logs(request):
    from .models import UserLog
    logs = UserLog.objects.select_related('user').all().order_by('-timestamp')
    users = User.objects.all()

    user_id = request.GET.get('user')
    date_param = request.GET.get('date')
    month = request.GET.get('month')
    year = request.GET.get('year')

    if user_id:
        logs = logs.filter(user_id=user_id)
    if date_param:
        logs = logs.filter(timestamp__date=date_param)
    if month:
        logs = logs.filter(timestamp__month=month)
    if year:
        logs = logs.filter(timestamp__year=year)

    # For dropdowns
    months = list(range(1, 13))
    today_date = date.today()
    years = list(range(today_date.year - 5, today_date.year + 2))

    return render(request, 'application/logs.html', {
        'logs': logs,
        'users': users,
        'selected_user': user_id,
        'selected_date': date_param,
        'selected_month': month,
        'selected_year': year,
        'months': months,
        'years': years,
    })
