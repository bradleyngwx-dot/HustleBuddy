from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Client


class UserSignUpForm(UserCreationForm):
    username = forms.CharField(
        max_length=15,
        help_text="Required. 15 characters or fewer."
        )
    class Meta:
        model = User
        fields = ["username", "password1", "password2"]

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "contact", "service_type", "notes"]
