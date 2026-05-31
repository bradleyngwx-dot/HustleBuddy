from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Appointment, Client

TIME_CHOICES = [
    (f"{hour:02d}:{minute:02d}", f"{hour:02d}:{minute:02d}")
    for hour in range(7, 23)
    for minute in (0, 30)
]


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

class AppointmentForm(forms.ModelForm):
    title = forms.CharField(max_length=100)
    date = forms.DateField(widget=forms.SelectDateWidget)
    # start_time = forms.ChoiceField(choices=TIME_CHOICES)
    # end_time = forms.ChoiceField(choices=[("", "---------")] + TIME_CHOICES, required=False)
    notes = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = Appointment
        fields = ["title", "date", "start_time", "end_time", "status", "notes"]
