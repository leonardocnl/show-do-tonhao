from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .perfis import EDITORES, JOGADORES

Usuario = get_user_model()


class CadastroELoginTests(TestCase):
    def test_cadastro_cria_jogador_e_faz_login(self):
        resposta = self.client.post(
            reverse("contas:cadastro"),
            {
                "username": "ana",
                "apelido": "Ana",
                "email": "ana@example.com",
                "password1": "senha-forte-9876",
                "password2": "senha-forte-9876",
            },
        )
        self.assertRedirects(resposta, reverse("quiz:inicio"))
        usuario = Usuario.objects.get(username="ana")
        self.assertTrue(usuario.groups.filter(name=JOGADORES).exists())
        self.assertFalse(usuario.groups.filter(name=EDITORES).exists())
        self.assertFalse(usuario.is_staff)
        self.assertEqual(int(self.client.session["_auth_user_id"]), usuario.pk)

    def test_cadastro_rejeita_senhas_diferentes(self):
        resposta = self.client.post(
            reverse("contas:cadastro"),
            {"username": "bia", "password1": "senha-forte-9876", "password2": "outra-senha-123"},
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Usuario.objects.filter(username="bia").exists())

    def test_login_e_logout(self):
        Usuario.objects.create_user("caio", password="senha-forte-9876")
        resposta = self.client.post(
            reverse("contas:login"), {"username": "caio", "password": "senha-forte-9876"}
        )
        self.assertRedirects(resposta, reverse("quiz:inicio"))
        self.client.post(reverse("contas:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_com_senha_errada_mostra_erro(self):
        Usuario.objects.create_user("duda", password="senha-forte-9876")
        resposta = self.client.post(reverse("contas:login"), {"username": "duda", "password": "errada"})
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_area_do_jogador_exige_login(self):
        resposta = self.client.get(reverse("quiz:jogo"))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse("contas:login"), resposta["Location"])

    def test_painel_admin_exige_login(self):
        resposta = self.client.get("/painel/")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/painel/login/", resposta["Location"])
