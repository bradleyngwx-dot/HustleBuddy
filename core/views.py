from datetime import date, datetime, timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import AppointmentForm, ClientForm, PaymentForm, PaymentStatusForm
from .models import Appointment, Client, Payment, TimeLog
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone


def shift_month(month_start, offset):
    month_index = (month_start.year * 12) + month_start.month - 1 + offset
    return date(month_index // 12, (month_index % 12) + 1, 1)


def appointment_duration_hours(appointment):
    if not appointment.end_time:
        return None

    start = datetime.combine(appointment.date, appointment.start_time)
    end = datetime.combine(appointment.date, appointment.end_time)

    if end <= start:
        return None

    hours = Decimal(str((end - start).total_seconds() / 3600))
    return hours.quantize(Decimal("0.01"))


def sync_time_log_for_appointment(appointment):
    if appointment.status != "completed":
        TimeLog.objects.filter(appointment=appointment).delete()
        return

    hours = appointment_duration_hours(appointment)
    if hours is None:
        TimeLog.objects.filter(appointment=appointment).delete()
        return

    TimeLog.objects.update_or_create(
        appointment=appointment,
        defaults={
            "client": appointment.client,
            "date": appointment.date,
            "hours": hours,
            "description": f"Completed appointment: {appointment.title}",
        },
    )


def sync_payment_for_appointment(appointment):
    if appointment.price <= 0:
        Payment.objects.filter(appointment=appointment).delete()
        return

    payment, created = Payment.objects.get_or_create(
        appointment=appointment,
        defaults={
            "client": appointment.client,
            "amount": appointment.price,
            "date_issued": appointment.date,
            "status": "pending",
            "description": f"Appointment: {appointment.title}",
        },
    )

    if not created:
        payment.client = appointment.client
        payment.amount = appointment.price
        payment.date_issued = appointment.date
        payment.description = f"Appointment: {appointment.title}"
        payment.save(update_fields=["client", "amount", "date_issued", "description"])


@login_required
def add_client(request):
    if request.method == "POST":
        form = ClientForm(request.POST)

        if form.is_valid():
            client = form.save(commit=False)
            client.owner = request.user
            client.save()
            return redirect("client_list")

    else:
        form = ClientForm()

    return render(request, "core/add_client.html", {"form": form})

@login_required
def client_list(request):
    clients = Client.objects.filter(owner=request.user)

    return render(request, "core/client_list.html", {"clients": clients})

@login_required
def client_detail(request, client_id):
    client = get_object_or_404(Client, id=client_id, owner=request.user)
    total_hours = client.time_logs.aggregate(Sum('hours'))['hours__sum'] or 0
    total_paid = client.payments.filter(status="paid").aggregate(Sum('amount'))['amount__sum'] or 0
    total_outstanding = client.payments.exclude(status="paid").aggregate(Sum('amount'))['amount__sum'] or 0
    return render(request, "core/client_detail.html", {
        "client": client,
        "total_hours": total_hours,
        "total_paid": total_paid,
        "total_outstanding": total_outstanding,
    })

@login_required
def edit_client(request, client_id):
    client = get_object_or_404(Client, id=client_id, owner=request.user)

    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)

        if form.is_valid():
            form.save()
            return redirect("client_detail", client_id=client.id)

    else:
        form = ClientForm(instance=client)

    return render(request, "core/edit_client.html", {"form": form, "client": client})

@login_required
def delete_client(request, client_id):
    client = get_object_or_404(Client, id=client_id, owner=request.user)

    if request.method == "POST":
        client.delete()
        return redirect("client_list")

    return render(request, "core/delete_client.html", {"client": client})

@login_required
def add_appointment(request, client_id):
    client = get_object_or_404(Client, id=client_id, owner=request.user)

    if request.method == "POST":
        form = AppointmentForm(request.POST)

        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.client = client
            appointment.owner = request.user
            
            # --- THE FIX: Convert empty string to None before saving ---
            if appointment.end_time == "":
                appointment.end_time = None
            # -----------------------------------------------------------

            appointment.save()
            sync_time_log_for_appointment(appointment)
            sync_payment_for_appointment(appointment)
            return redirect("client_detail", client_id=client.id)

    else:
        form = AppointmentForm()

    return render(request, "core/add_appointment.html", {"form": form, "client": client})

@login_required
def delete_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, owner=request.user)

    if request.method == "POST":
        appointment.delete()
        return redirect("client_detail", client_id=appointment.client.id)

    return render(request, "core/delete_appointment.html", {"appointment": appointment})

@login_required
def edit_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, owner=request.user)

    if request.method == "POST":
        form = AppointmentForm(request.POST, instance=appointment)

        if form.is_valid():
            # Stop the save temporarily using commit=False
            apt = form.save(commit=False)
            
            # --- THE FIX: Convert empty string to None before saving ---
            if apt.end_time == "":
                apt.end_time = None
            # -----------------------------------------------------------
                
            apt.save()
            sync_time_log_for_appointment(apt)
            sync_payment_for_appointment(apt)
            return redirect("client_detail", client_id=apt.client.id)

    else:
        form = AppointmentForm(instance=appointment)

    return render(request, "core/edit_appointment.html", {"form": form, "appointment": appointment})

@login_required
def schedule(request):
    appointments = Appointment.objects.filter(owner=request.user).select_related("client").order_by("date", "start_time")
    selected_year = request.GET.get("year")
    selected_month = request.GET.get("month")
    selected_day = request.GET.get("day")

    if selected_year:
        appointments = appointments.filter(date__year=selected_year)

    if selected_month:
        appointments = appointments.filter(date__month=selected_month)

    if selected_day:
        appointments = appointments.filter(date__day=selected_day)

    return render(request, "core/schedule.html", {
        "appointments": appointments,
        "selected_year": selected_year,
        "selected_month": selected_month,
        "selected_day": selected_day,
    })

@login_required
def log_payment(request, client_id):
    client = get_object_or_404(Client, id=client_id, owner=request.user)
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.client = client
            payment.save()
            return redirect("client_detail", client_id=client.id)
    else:
        form = PaymentForm()
    return render(request, "core/log_payment.html", {"form": form, "client": client})

@login_required
def edit_payment(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id, client__owner=request.user)
    form_class = PaymentStatusForm if payment.appointment_id else PaymentForm
    if request.method == "POST":
        form = form_class(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            return redirect("client_detail", client_id=payment.client.id)
    else:
        form = form_class(instance=payment)
    return render(request, "core/edit_payment.html", {"form": form, "payment": payment})

@login_required
def delete_payment(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id, client__owner=request.user)
    client_id = payment.client.id
    if request.method == "POST":
        payment.delete()
        return redirect("client_detail", client_id=client_id)
    return render(request, "core/delete_payment.html", {"payment": payment})

@login_required
def dashboard(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    next_month = (month_start + timedelta(days=32)).replace(day=1)
    selected_hours_range = request.GET.get("hours_range", "3")
    if selected_hours_range not in {"3", "12"}:
        selected_hours_range = "3"
    hours_month_count = int(selected_hours_range)

    time_logs = TimeLog.objects.filter(
        client__owner=request.user
    )
    hours = time_logs.filter(date__gte=month_start, date__lt=next_month).aggregate(total=Sum("hours", default=0))["total"]
    paid = Payment.objects.filter(client__owner=request.user, status="paid").filter(
        Q(date_paid__gte=month_start, date_paid__lt=next_month)
        | Q(date_paid__isnull=True, date_issued__gte=month_start, date_issued__lt=next_month)
    )
    total_hours_this_month = hours or Decimal("0")
    total_paid_this_month = paid.aggregate(total=Sum("amount", default=0))["total"] or Decimal("0")
    if total_hours_this_month > 0:
        effective_hourly_rate = total_paid_this_month / total_hours_this_month
    else:
        effective_hourly_rate = Decimal("0")
    appointments_today = Appointment.objects.filter(owner=request.user, date=today)
    upcoming_appointments = (Appointment.objects.filter(owner=request.user,date__gte=today,date__lte=today + timedelta(days=7),)
        .filter(status="upcoming").order_by("date", "start_time"))

    chart_months = [
        shift_month(month_start, offset)
        for offset in range(-(hours_month_count - 1), 1)
    ]
    chart_month_keys = [month.strftime("%Y-%m") for month in chart_months]
    monthly_hours = {key: Decimal("0") for key in chart_month_keys}
    monthly_paid = {key: Decimal("0") for key in chart_month_keys}

    for row in (
        time_logs.filter(date__gte=chart_months[0], date__lt=next_month)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("hours"))
        .order_by("month")
    ):
        key = row["month"].strftime("%Y-%m")
        monthly_hours[key] = row["total"] or Decimal("0")

    for row in (
        Payment.objects.filter(
            client__owner=request.user,
            status="paid",
            date_paid__gte=chart_months[0],
            date_paid__lt=next_month,
        )
        .annotate(month=TruncMonth("date_paid"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    ):
        key = row["month"].strftime("%Y-%m")
        monthly_paid[key] = row["total"] or Decimal("0")

    for row in (
        Payment.objects.filter(
            client__owner=request.user,
            status="paid",
            date_paid__isnull=True,
            date_issued__gte=chart_months[0],
            date_issued__lt=next_month,
        )
        .annotate(month=TruncMonth("date_issued"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    ):
        key = row["month"].strftime("%Y-%m")
        monthly_paid[key] += row["total"] or Decimal("0")

    chart_data = {
        "labels": [month.strftime("%b %y") for month in chart_months],
        "hours": [float(monthly_hours[key]) for key in chart_month_keys],
        "paid": [float(monthly_paid[key]) for key in chart_month_keys],
    }

    payment_totals = Payment.objects.filter(client__owner=request.user).aggregate(
        paid=Sum("amount", filter=Q(status="paid"), default=0),
        outstanding=Sum("amount", filter=Q(status="pending"), default=0),
        overdue=Sum("amount", filter=Q(status="overdue"), default=0),
    )
    payment_pie_data = {
        "labels": ["Paid", "Outstanding", "Overdue"],
        "values": [
            float(payment_totals["paid"] or 0),
            float(payment_totals["outstanding"] or 0),
            float(payment_totals["overdue"] or 0),
        ],
    }

    context = {
        "total_hours_this_month": total_hours_this_month,
        "total_paid_this_month": total_paid_this_month,
        "effective_hourly_rate": effective_hourly_rate,
        "appointments_today": appointments_today,
        "upcoming_appointments": upcoming_appointments,
        "chart_data": chart_data,
        "selected_hours_range": selected_hours_range,
        "payment_pie_data": payment_pie_data,
    }

    return render(request, "core/dashboard.html", context)
