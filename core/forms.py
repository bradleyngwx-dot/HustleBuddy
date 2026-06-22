from django import forms
from .models import Appointment, Client

TIME_CHOICES = [
    (f"{hour:02d}:{minute:02d}", f"{hour:02d}:{minute:02d}")
    for hour in range(7, 23)
    for minute in (0, 30)
]


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
