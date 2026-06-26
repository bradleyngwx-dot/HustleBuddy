from django.db import models
from django.contrib.auth.models import User


#Client Model
class Client(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=100, blank=True)
    service_type = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

#Appointmenmt Model
class Appointment(models.Model):
    STATUS_CHOICES = [
        ("upcoming", "Upcoming"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("rescheduled", "Rescheduled"),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="appointments")
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="upcoming")
    notes = models.TextField(blank=True)

class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_issued = models.DateField()
    date_paid = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"${self.amount} from {self.client.name} — {self.status}"


class TimeLog(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="time_logs")
    date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2) 
    description = models.CharField(max_length=255, help_text="e.g., Drafted initial logo concepts")
    created_at = models.DateTimeField(auto_now_add=True) 
    def __str__(self):
        return f"{self.hours} hours for {self.client.name} on {self.date}"
    
