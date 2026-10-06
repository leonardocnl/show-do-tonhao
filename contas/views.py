from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import CadastroForm


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("quiz:inicio")

    if request.method == "POST":
        form = CadastroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            messages.success(request, "Conta criada! Escolha um tema e boa sorte.")
            return redirect("quiz:inicio")
    else:
        form = CadastroForm()

    return render(request, "contas/cadastro.html", {"form": form})
