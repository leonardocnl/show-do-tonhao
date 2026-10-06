/* Menu "Aparência": modo claro/escuro, tema de cores e fonte.
   As escolhas ficam no localStorage; o <head> (base.html) aplica tudo antes de pintar a página. */
(function () {
  var raiz = document.documentElement;
  var menu = document.querySelector('[data-aparencia]');
  if (!menu) { return; }

  var botao = menu.querySelector('.ap-botao');
  var painel = menu.querySelector('.ap-painel');
  var fonte = menu.querySelector('#ap-fonte');

  function guardar(chave, valor) {
    try { localStorage.setItem(chave, valor); } catch (erro) { /* sem armazenamento */ }
  }

  function aplicarFonte(nome) {
    raiz.style.setProperty('--fonte', '"' + nome + '", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif');
  }

  function marcar() {
    var modo = raiz.classList.contains('dark') ? 'dark' : 'light';
    var tema = raiz.getAttribute('data-palette') || 'cozy';
    menu.querySelectorAll('[data-modo]').forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-modo') === modo ? 'true' : 'false');
    });
    menu.querySelectorAll('[data-tema]').forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-tema') === tema ? 'true' : 'false');
    });
  }

  function abrir(aberto) {
    painel.hidden = !aberto;
    botao.setAttribute('aria-expanded', aberto ? 'true' : 'false');
  }

  botao.addEventListener('click', function () { abrir(painel.hidden); });
  document.addEventListener('click', function (evento) {
    if (!painel.hidden && !menu.contains(evento.target)) { abrir(false); }
  });
  document.addEventListener('keydown', function (evento) {
    if (evento.key === 'Escape' && !painel.hidden) { abrir(false); botao.focus(); }
  });

  menu.querySelectorAll('[data-modo]').forEach(function (b) {
    b.addEventListener('click', function () {
      var modo = b.getAttribute('data-modo');
      raiz.classList.toggle('dark', modo === 'dark');
      guardar('tonhao-tema', modo);
      marcar();
    });
  });

  menu.querySelectorAll('[data-tema]').forEach(function (b) {
    b.addEventListener('click', function () {
      var tema = b.getAttribute('data-tema');
      if (tema === 'cozy') { raiz.removeAttribute('data-palette'); } else { raiz.setAttribute('data-palette', tema); }
      guardar('tonhao-paleta', tema);
      marcar();
    });
  });

  fonte.addEventListener('change', function () {
    aplicarFonte(fonte.value);
    guardar('tonhao-fonte', fonte.value);
  });

  try { fonte.value = localStorage.getItem('tonhao-fonte') || 'Nunito'; } catch (erro) { /* mantém o padrão */ }
  if (!fonte.value) { fonte.value = 'Nunito'; }
  marcar();
})();
