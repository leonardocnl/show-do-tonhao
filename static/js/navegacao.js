/* Menu responsivo e menu do usuário. */
(function () {
  var botao = document.getElementById('btn-menu');
  var menu = document.getElementById('menu');
  if (botao && menu) {
    botao.addEventListener('click', function () {
      var aberto = menu.classList.toggle('hidden') === false;
      botao.setAttribute('aria-expanded', aberto ? 'true' : 'false');
      menu.classList.toggle('flex', aberto);
    });
  }

  var usuario = document.getElementById('menu-usuario');
  if (usuario) {
    document.addEventListener('click', function (evento) {
      if (!usuario.contains(evento.target)) { usuario.removeAttribute('open'); }
    });
    document.addEventListener('keydown', function (evento) {
      if (evento.key === 'Escape') { usuario.removeAttribute('open'); }
    });
  }
})();
