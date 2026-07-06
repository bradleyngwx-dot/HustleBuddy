from django import forms
from django.utils import timezone
from .models import Appointment, Client, Payment

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
        fields = ["title", "date", "start_time", "end_time", "price", "status", "notes"]

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if status == "completed":
            if not end_time:
                self.add_error("end_time", "Add an end time before marking this appointment completed.")
            elif start_time and end_time <= start_time:
                self.add_error("end_time", "End time must be after start time.")

        return cleaned_data

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'date_issued', 'date_paid', 'status', 'description']
        widgets = {
            'date_issued': forms.DateInput(attrs={'type': 'date'}),
            'date_paid': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        date_issued = cleaned_data.get("date_issued")
        date_paid = cleaned_data.get("date_paid")

        if status == "paid" and not date_paid:
            cleaned_data["date_paid"] = date_issued

        return cleaned_data


class PaymentStatusForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["status", "date_paid"]
        widgets = {
            "date_paid": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        date_paid = cleaned_data.get("date_paid")

        if status == "paid" and not date_paid:
            cleaned_data["date_paid"] = timezone.localdate()
        elif status != "paid":
            cleaned_data["date_paid"] = None

        return cleaned_data
