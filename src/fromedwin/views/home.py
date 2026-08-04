from django.conf import settings
from django.shortcuts import render


def home(request):
    version = ".".join(str(part) for part in settings.VERSION)
    return render(request, "home.html", {"version": version})
