from django.shortcuts import render
from django.contrib.auth.decorators import login_required


def home(request):
    # Home accesible a todo el mundo (muestra login si no está autenticado)
    return render(request, "home.html")
