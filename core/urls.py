from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", views.client_list, name="home"),
    path("clients/", views.client_list, name="client_list"),
    path("schedule/", views.schedule, name="schedule"),
    path("clients/add/", views.add_client, name="add_client"),
    path("clients/<int:client_id>/", views.client_detail, name="client_detail"),
    path("clients/<int:client_id>/edit/", views.edit_client, name="edit_client"),
    path("clients/<int:client_id>/delete/", views.delete_client, name="delete_client"),
    path("signup/", RedirectView.as_view(pattern_name="account_signup", permanent=False), name="signup"),
    path("clients/<int:client_id>/appointments/add/", views.add_appointment, name="add_appointment"),
    path("appointments/<int:appointment_id>/edit/", views.edit_appointment, name="edit_appointment"),
    path("appointments/<int:appointment_id>/delete/", views.delete_appointment, name="delete_appointment"),
    path("client/<int:client_id>/log-time/", views.log_time, name="log_time"),
    path("clients/<int:client_id>/log-payment/", views.log_payment, name="log_payment"),
    path("payments/<int:payment_id>/edit/", views.edit_payment, name="edit_payment"),
    path("payments/<int:payment_id>/delete/", views.delete_payment, name="delete_payment"),
]
