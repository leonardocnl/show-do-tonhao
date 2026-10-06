/* Tela de pergunta: atalhos A-D e confirmação de ações que encerram a partida. */
(function () {
  var form = document.getElementById('form-resposta');
  if (!form) { return; }

  document.addEventListener('keydown', function (evento) {
    if (evento.ctrlKey || evento.metaKey || evento.altKey) { return; }
    var alvo = evento.target;
    if (alvo && /^(textarea|select)$/i.test(alvo.tagName)) { return; }

    var posicao = 'ABCD'.indexOf(String(evento.key).toUpperCase());
    if (String(evento.key).length !== 1 || posicao < 0) { return; }

    var radio = form.querySelectorAll('.alt-input')[posicao];
    if (radio && !radio.disabled) {
      radio.checked = true;
      radio.focus();
    }
  });

  form.querySelectorAll('[data-confirmar]').forEach(function (botao) {
    botao.addEventListener('click', function (evento) {
      if (!window.confirm(botao.getAttribute('data-confirmar'))) {
        evento.preventDefault();
      }
    });
  });
})();
