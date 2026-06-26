"""
URL configuration for the HustleBuddy project.
"""
from django.contrib import admin
from django.urls import include, path

# Tell Django's Admin panel to use our custom login template
admin.site.login_template = 'registration/login.html'

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("accounts/", include("allauth.urls")),
]
