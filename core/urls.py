from django.urls import path

from . import views

urlpatterns = [
    path("", views.client_list, name="home"),
    path("clients/", views.client_list, name="client_list"),
    path("clients/add/", views.add_client, name="add_client"),
    path("signup/", views.signup, name="signup"),
]
