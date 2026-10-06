from django.urls import path

from . import views

app_name = "quiz"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("jogar/", views.iniciar, name="iniciar"),
    path("partida/", views.jogo, name="jogo"),
    path("partida/responder/", views.responder, name="responder"),
    path("partida/ajuda/<str:tipo>/", views.ajuda, name="ajuda"),
    path("partida/parar/", views.parar, name="parar"),
    path("partida/abandonar/", views.abandonar, name="abandonar"),
    path("partida/<int:pk>/resultado/", views.resultado, name="resultado"),
    path("ranking/", views.ranking, name="ranking"),
    path("historico/", views.historico, name="historico"),
    # área do editor
    path("editor/perguntas/", views.PerguntaListView.as_view(), name="perguntas"),
    path("editor/perguntas/nova/", views.PerguntaCreateView.as_view(), name="pergunta_nova"),
    path("editor/perguntas/<int:pk>/editar/", views.PerguntaUpdateView.as_view(), name="pergunta_editar"),
    path("editor/perguntas/<int:pk>/excluir/", views.PerguntaDeleteView.as_view(), name="pergunta_excluir"),
]
