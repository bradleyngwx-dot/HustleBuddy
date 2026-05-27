from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import ClientForm, UserSignUpForm
from .models import Client

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

def signup(request):
    if request.method == "POST":
        form = UserSignUpForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("login")

    else:
        form = UserSignUpForm()

    return render(request, "core/signup.html", {"form": form})
