# Show do Tonhão

Jogo de perguntas e respostas no formato "Show do Milhão", feito em Django para o Trabalho Prático 1 de GAC116 (Programação Web) — UFLA. O jogador responde 16 perguntas de dificuldade crescente, usa ajudas e tenta chegar ao prêmio de R$ 1.000.000. O Tonhão, coordenador do curso de Ciência da Computação, é o apresentador.

## Integrantes

| Nome | Matrícula | GitHub |
| --- | --- | --- |
| Leonardo Carvalho Silva | _preencher_ | _preencher_ |
| _preencher_ | _preencher_ | _preencher_ |
| _preencher_ | _preencher_ | _preencher_ |

## Tecnologias

- Python 3 e Django 5.1/5.2 (padrão MVT), SQLite
- Modelo de usuário customizado (`contas.Usuario`)
- **Tailwind CSS v4** (framework CSS), fonte Nunito (Google Fonts)
- django-jazzmin para o painel administrativo (`/painel/`)
- Estilo próprio "Cozy": cantos arredondados, bordas de 4 px, sombra só por baixo, paleta de marrons com destaques amarelo, laranja e verde, tema claro e escuro

## Como instalar e rodar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_quiz        # carrega 704 perguntas (176 por categoria, 44 por nível de dificuldade) (use --demo para criar usuários de teste)
python manage.py createsuperuser  # administrador
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/` (jogo) e `http://127.0.0.1:8000/painel/` (administração).
O CSS compilado (`static/css/tailwind.css`) já está no repositório: **não é preciso instalar Node** para rodar.

`seed_quiz --demo` cria `jogador_demo` e `editor_demo` (senha `tonhao-demo-123`). Use apenas em desenvolvimento.
A área do editor fica em `/editor/perguntas/`.

Testes: `python manage.py test`

### Tailwind (só se for alterar o visual)

O código-fonte do estilo é `static/src/tailwind.css`; as classes são lidas dos templates em `templates/`.
Depois de mexer neles, recompile com o executável standalone do Tailwind (não precisa de Node):

```bash
# baixe uma vez: https://github.com/tailwindlabs/tailwindcss/releases/latest (tailwindcss-linux-x64, -macos-arm64, ...)
./tailwindcss -i static/src/tailwind.css -o static/css/tailwind.css --minify          # compila
./tailwindcss -i static/src/tailwind.css -o static/css/tailwind.css --watch           # recompila ao salvar
```

Com Node, o equivalente é `npx @tailwindcss/cli -i static/src/tailwind.css -o static/css/tailwind.css --minify`.
Faça commit do `static/css/tailwind.css` gerado.

## Funcionalidades

- Cadastro, login e logout; novos usuários entram no grupo **Jogadores**
- Partida com 16 perguntas sorteadas por faixa de dificuldade (1–4, 5–8, 9–12, 13–16)
- Tabela de prêmios de R$ 1.000 a R$ 1.000.000, com paradas garantidas nos níveis 5, 10 e 15
- Em cada pergunta: acertar, parar (leva o valor de parar) ou errar (cai para o valor de errar)
- Ajudas: **cartas** (eliminam 1 a 3 erradas), **placas** (opinião da plateia), **Tonhão** (dica) e **pular** (até 3 vezes)
- Ranking (top 10) e histórico de partidas do jogador
- CRUD de perguntas com 4 alternativas e 1 correta, com filtros e paginação
- Janela de confirmação customizada para ações destrutivas ou de abandono
- Interface responsiva com layout adaptado para celulares e tablets (sem rolagem horizontal em tabelas e telas principais)
- Painel administrativo com filtros (`list_filter`) e busca
- Menu **Aparência**: modo claro/escuro, 6 esquemas de cores (Cozy, Céu, Lagoa, Crepúsculo, Grafite, Framboesa) e 8 fontes; a escolha fica salva no navegador
- Números tabulares (largura fixa) em toda a interface

## Capturas de tela

1. [Início](docs/capturas/inicio.png)
2. [Jogo](docs/capturas/jogo.png)
3. [Resultado](docs/capturas/resultado.png)
4. [Ranking](docs/capturas/ranking.png)
5. [Lista de perguntas](docs/capturas/perguntas.png)
6. [Menu Aparência](docs/capturas/aparencia.png)

## Perfis e permissões

| Ação | Visitante | Jogador | Editor | Administrador |
| --- | :-: | :-: | :-: | :-: |
| Ver página inicial | ✔ | ✔ | ✔ | ✔ |
| Cadastrar e entrar | ✔ | ✔ | ✔ | ✔ |
| Jogar, ver ranking e histórico | ✖ | ✔ | ✔ | ✔ |
| Listar perguntas | ✖ | ✖ | ✔ | ✔ |
| Criar, editar e excluir perguntas e categorias | ✖ | ✖ | ✔ | ✔ |
| Acessar `/painel/` e gerenciar usuários | ✖ | ✖ | ✖ | ✔ |

Os grupos **Jogadores** e **Editores** são criados automaticamente após o `migrate`. Administradores são usuários `is_staff`/`is_superuser`. Visitantes são levados ao login; usuários logados sem permissão veem uma página 403.

## Estrutura e arquitetura

```
config/              configurações, urls, wsgi/asgi
contas/              app de contas: usuário customizado, cadastro/login, perfis (grupos)
quiz/                app do jogo
  regras.py          DOMÍNIO: regras puras (prêmios, paradas, escada), sem Django
  services.py        CASOS DE USO: iniciar, responder, parar, ajudas (acesso ao banco)
  models.py          PERSISTÊNCIA: entidades e relacionamentos
  forms.py, views.py INTERFACE: formulários, telas e permissões
  seed_data.py       perguntas iniciais (comando seed_quiz)
static/
  src/tailwind.css   fonte do Tailwind: tokens de tema e componentes
  css/               CSS compilado (tailwind.css) e ajustes do painel (admin-tonhao.css)
  js/                aparencia.js (modo, cores e fonte), navegacao.js (menu), jogo.js (atalhos)
templates/
  layouts/           base.html e navegação
  components/        peças reutilizáveis (campo, ícones, mensagens, paginação)
  contas/, quiz/     telas de cada app
```

Dependências apontam para dentro: `views` → `services` → `regras`. As regras do jogo não importam Django
e são testadas isoladamente; as views não contêm regra de negócio.

## Fluxo de Git

- `main`: versão estável
- `develop`: integração
- `feature/*`: uma branch por funcionalidade, mesclada em `develop` por merge/PR

Cada integrante deve ter ao menos 2 commits com a própria autoria.

## Checklist do trabalho

- [x] Projeto Django com 2 apps (`contas`, `quiz`) e usuário customizado
- [x] CRUD completo (perguntas) com validação de formulário
- [x] Autenticação e perfis com permissões (Jogador, Editor, Administrador)
- [x] Painel admin com `list_filter`
- [x] Tailwind CSS e templates com herança
- [x] Testes automatizados
- [x] Janela de confirmação customizada
- [x] Interface responsiva para celulares e tablets
- [ ] Repositório público no GitHub com os colaboradores adicionados
- [ ] Tema aprovado pelo professor
