from datetime import date, datetime, timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import AppointmentForm, ClientForm, PaymentForm, PaymentStatusForm
from .models import Appointment, Client, Payment, TimeLog
from django.db.models import Case, IntegerField, Q, Sum, Value, When
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


def mark_overdue_appointment_payments(user):
    overdue_cutoff = timezone.localdate() - timedelta(days=7)
    return Payment.objects.filter(
        client__owner=user,
        appointment__isnull=False,
        appointment__date__lte=overdue_cutoff,
        status="pending",
    ).update(status="overdue", date_paid=None)


def paid_payments_between(user, start_date, end_date):
    return Payment.objects.filter(client__owner=user, status="paid").filter(
        Q(date_paid__gte=start_date, date_paid__lt=end_date)
        | Q(
            date_paid__isnull=True,
            date_issued__gte=start_date,
            date_issued__lt=end_date,
        )
    )


def format_dashboard_date(value):
    return f"{value.strftime('%b')} {value.day}, {value.year}"


def period_change(current_value, previous_value, better_when_higher=True):
    current_value = Decimal(str(current_value or 0))
    previous_value = Decimal(str(previous_value or 0))

    if current_value == previous_value:
        return {"label": "No change", "tone_class": "change-neutral"}

    if previous_value == 0:
        tone_class = "change-positive" if better_when_higher else "change-negative"
        return {"label": "New this period", "tone_class": tone_class}

    change = ((current_value - previous_value) / previous_value) * Decimal("100")
    tone_class = "change-positive" if current_value > previous_value else "change-negative"
    if not better_when_higher:
        tone_class = "change-negative" if current_value > previous_value else "change-positive"

    sign = "+" if change > 0 else ""
    return {
        "label": f"{sign}{change.quantize(Decimal('1'))}% vs previous period",
        "tone_class": tone_class,
    }


def save_appointment_for_client(form, client, user):
    appointment = form.save(commit=False)
    appointment.client = client
    appointment.owner = user

    if appointment.end_time == "":
        appointment.end_time = None

    appointment.save()
    sync_time_log_for_appointment(appointment)
    sync_payment_for_appointment(appointment)
    return appointment

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
    mark_overdue_appointment_payments(request.user)
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
            save_appointment_for_client(form, client, request.user)
            return redirect("client_detail", client_id=client.id)

    else:
        form = AppointmentForm()

    return render(request, "core/add_appointment.html", {"form": form, "client": client})


@login_required
def add_appointment_global(request):
    clients = Client.objects.filter(owner=request.user).order_by("name")
    form = AppointmentForm(request.POST or None)
    selected_client_id = request.POST.get("client") if request.method == "POST" else None

    if request.method == "POST":
        selected_client = clients.filter(id=selected_client_id).first()
        if selected_client is None:
            form.add_error(None, "Choose a client for this appointment.")
        elif form.is_valid():
            save_appointment_for_client(form, selected_client, request.user)
            return redirect("dashboard")

    return render(
        request,
        "core/add_appointment.html",
        {
            "form": form,
            "client": None,
            "clients": clients,
            "selected_client_id": selected_client_id,
        },
    )

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
    mark_overdue_appointment_payments(request.user)
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
def payment_list(request):
    mark_overdue_appointment_payments(request.user)
    payments = (
        Payment.objects.filter(client__owner=request.user)
        .select_related("client", "appointment")
        .annotate(
            status_rank=Case(
                When(status="overdue", then=Value(0)),
                When(status="pending", then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("status_rank", "date_issued", "client__name")
    )
    totals = payments.aggregate(
        paid=Sum("amount", filter=Q(status="paid"), default=0),
        outstanding=Sum("amount", filter=Q(status="pending"), default=0),
        overdue=Sum("amount", filter=Q(status="overdue"), default=0),
    )
    return render(
        request,
        "core/payment_list.html",
        {
            "payments": payments,
            "payment_totals": totals,
        },
    )


@login_required
def time_log_list(request):
    time_logs = (
        TimeLog.objects.filter(client__owner=request.user)
        .select_related("client", "appointment")
        .order_by("-date", "client__name")
    )
    total_hours = time_logs.aggregate(total=Sum("hours", default=0))["total"] or Decimal("0")
    return render(
        request,
        "core/time_log_list.html",
        {
            "time_logs": time_logs,
            "total_hours": total_hours,
        },
    )


@login_required
def settings(request):
    return render(request, "core/settings.html")


@login_required
def dashboard(request):
    today = timezone.localdate()
    mark_overdue_appointment_payments(request.user)
    month_start = today.replace(day=1)
    next_month = (month_start + timedelta(days=32)).replace(day=1)
    selected_period = request.GET.get("period") or request.GET.get("hours_range", "3")
    if selected_period not in {"1", "3", "12"}:
        selected_period = "3"
    selected_hours_range = selected_period
    hours_month_count = int(selected_period)

    time_logs = TimeLog.objects.filter(
        client__owner=request.user
    )
    total_hours_this_month = time_logs.filter(
        date__gte=month_start,
        date__lt=next_month,
    ).aggregate(total=Sum("hours", default=0))["total"] or Decimal("0")
    total_paid_this_month = paid_payments_between(
        request.user,
        month_start,
        next_month,
    ).aggregate(total=Sum("amount", default=0))["total"] or Decimal("0")
    if total_hours_this_month > 0:
        effective_hourly_rate = total_paid_this_month / total_hours_this_month
    else:
        effective_hourly_rate = Decimal("0")
    appointments_today = Appointment.objects.filter(owner=request.user, date=today)
    upcoming_appointments = (
        Appointment.objects.filter(
            owner=request.user,
            date__gte=today,
            date__lte=today + timedelta(days=7),
            status__in=["upcoming", "rescheduled"],
        )
        .select_related("client")
        .order_by("date", "start_time")
    )

    chart_months = [
        shift_month(month_start, offset)
        for offset in range(-(hours_month_count - 1), 1)
    ]
    period_start = chart_months[0]
    period_end = next_month
    previous_period_start = shift_month(period_start, -hours_month_count)
    previous_period_end = period_start
    period_last_day = period_end - timedelta(days=1)

    period_hours = time_logs.filter(
        date__gte=period_start,
        date__lt=period_end,
    ).aggregate(total=Sum("hours", default=0))["total"] or Decimal("0")
    previous_period_hours = time_logs.filter(
        date__gte=previous_period_start,
        date__lt=previous_period_end,
    ).aggregate(total=Sum("hours", default=0))["total"] or Decimal("0")

    period_revenue = paid_payments_between(
        request.user,
        period_start,
        period_end,
    ).aggregate(total=Sum("amount", default=0))["total"] or Decimal("0")
    previous_period_revenue = paid_payments_between(
        request.user,
        previous_period_start,
        previous_period_end,
    ).aggregate(total=Sum("amount", default=0))["total"] or Decimal("0")

    period_unpaid_payments = Payment.objects.filter(
        client__owner=request.user,
        status__in=["pending", "overdue"],
        date_issued__gte=period_start,
        date_issued__lt=period_end,
    )
    previous_period_unpaid_payments = Payment.objects.filter(
        client__owner=request.user,
        status__in=["pending", "overdue"],
        date_issued__gte=previous_period_start,
        date_issued__lt=previous_period_end,
    )
    period_outstanding = period_unpaid_payments.aggregate(
        total=Sum("amount", default=0)
    )["total"] or Decimal("0")
    previous_period_outstanding = previous_period_unpaid_payments.aggregate(
        total=Sum("amount", default=0)
    )["total"] or Decimal("0")
    unpaid_payment_count = period_unpaid_payments.count()

    period_appointments = Appointment.objects.filter(
        owner=request.user,
        date__gte=period_start,
        date__lt=period_end,
    )
    previous_period_appointments = Appointment.objects.filter(
        owner=request.user,
        date__gte=previous_period_start,
        date__lt=previous_period_end,
    )
    period_appointment_count = period_appointments.count()
    previous_period_appointment_count = previous_period_appointments.count()

    chart_month_keys = [month.strftime("%Y-%m") for month in chart_months]
    monthly_hours = {key: Decimal("0") for key in chart_month_keys}
    monthly_paid = {key: Decimal("0") for key in chart_month_keys}

    for row in (
        time_logs.filter(date__gte=period_start, date__lt=period_end)
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
            date_paid__gte=period_start,
            date_paid__lt=period_end,
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
            date_issued__gte=period_start,
            date_issued__lt=period_end,
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
    payment_chart_total = (
        (payment_totals["paid"] or Decimal("0"))
        + (payment_totals["outstanding"] or Decimal("0"))
        + (payment_totals["overdue"] or Decimal("0"))
    )
    payment_pie_data = {
        "labels": ["Paid", "Outstanding", "Overdue"],
        "values": [
            float(payment_totals["paid"] or 0),
            float(payment_totals["outstanding"] or 0),
            float(payment_totals["overdue"] or 0),
        ],
    }
    outstanding_payments = (
        Payment.objects.filter(
            client__owner=request.user,
            status__in=["pending", "overdue"],
        )
        .select_related("client", "appointment")
        .annotate(
            status_rank=Case(
                When(status="overdue", then=Value(0)),
                When(status="pending", then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("status_rank", "date_issued", "client__name")[:8]
    )
    overdue_payment_count = Payment.objects.filter(
        client__owner=request.user,
        status="overdue",
    ).count()
    pending_payment_count = Payment.objects.filter(
        client__owner=request.user,
        status="pending",
    ).count()

    completed_but_unpaid = Payment.objects.filter(
        client__owner=request.user,
        appointment__status="completed",
        status__in=["pending", "overdue"],
    ).aggregate(total=Sum("amount", default=0))["total"] or Decimal("0")

    upcoming_revenue = Appointment.objects.filter(
        owner=request.user,
        date__gte=today,
        status__in=["upcoming", "rescheduled"],
    ).aggregate(total=Sum("price", default=0))["total"] or Decimal("0")

    paid_payments_with_dates = Payment.objects.filter(
        client__owner=request.user,
        status="paid",
        date_paid__isnull=False,
    )
    payment_day_counts = [
        (payment.date_paid - payment.date_issued).days
        for payment in paid_payments_with_dates
        if payment.date_paid >= payment.date_issued
    ]
    if payment_day_counts:
        average_days_to_payment = sum(payment_day_counts) / len(payment_day_counts)
    else:
        average_days_to_payment = 0

    selected_period_label = {
        "1": "This month",
        "3": "Past 3 months",
        "12": "Past 12 months",
    }[selected_period]
    previous_period_label = (
        "previous month"
        if hours_month_count == 1
        else f"previous {hours_month_count} months"
    )
    dashboard_user_name = request.user.get_short_name() or request.user.username

    context = {
        "dashboard_user_name": dashboard_user_name,
        "total_hours_this_month": total_hours_this_month,
        "total_paid_this_month": total_paid_this_month,
        "effective_hourly_rate": effective_hourly_rate,
        "period_revenue": period_revenue,
        "period_outstanding": period_outstanding,
        "period_hours": period_hours,
        "period_appointment_count": period_appointment_count,
        "unpaid_payment_count": unpaid_payment_count,
        "selected_period": selected_period,
        "selected_period_label": selected_period_label,
        "selected_period_date_range": (
            f"{format_dashboard_date(period_start)} - "
            f"{format_dashboard_date(period_last_day)}"
        ),
        "previous_period_label": previous_period_label,
        "revenue_change": period_change(period_revenue, previous_period_revenue),
        "outstanding_change": period_change(
            period_outstanding,
            previous_period_outstanding,
            better_when_higher=False,
        ),
        "hours_change": period_change(period_hours, previous_period_hours),
        "appointments_change": period_change(
            period_appointment_count,
            previous_period_appointment_count,
        ),
        "completed_but_unpaid": completed_but_unpaid,
        "upcoming_revenue": upcoming_revenue,
        "average_days_to_payment": average_days_to_payment,
        "appointments_today": appointments_today,
        "upcoming_appointments": upcoming_appointments,
        "chart_data": chart_data,
        "selected_hours_range": selected_hours_range,
        "payment_pie_data": payment_pie_data,
        "payment_chart_total": payment_chart_total,
        "payment_totals": payment_totals,
        "outstanding_payments": outstanding_payments,
        "overdue_payment_count": overdue_payment_count,
        "pending_payment_count": pending_payment_count,
    }

    return render(request, "core/dashboard.html", context)
