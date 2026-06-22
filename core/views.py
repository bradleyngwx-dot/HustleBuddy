from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import AppointmentForm, ClientForm
from .models import Appointment, Client

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

    return render(request, "core/client_detail.html", {"client": client})

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
            return redirect("client_detail", client_id=appointment.client.id)

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
