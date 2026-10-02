# Caderneta Digital

Aplicativo web (PWA) para controlar as vendas fiado e os pedidos de entrega do **Hortifrúti Recanto Verde**, em Jaru (RO). Substitui a caderneta de papel por um registro rápido no celular, que funciona mesmo sem internet e sincroniza com o servidor quando a conexão volta.

Projeto desenvolvido na disciplina de Projeto de Software (Experiências Práticas 1, 2 e 3), com foco no ODS 8, meta 8.3.

## Funcionalidades

- Busca de clientes por nome com saldo do fiado
- Anotar compra fiado e registrar pagamento (dinheiro, Pix ou cartão)
- Funcionamento offline com fila de sincronização e envio sem duplicidade
- Extrato do mês enviado pelo WhatsApp
- Pedidos de entrega com status (novo, separado, entregue, cancelado)
- Resumo mensal: total a receber, recebido no mês e quem mais deve
- Login com perfis de proprietária e colaborador

## Tecnologias

| Parte | Tecnologia |
| --- | --- |
| Front-end | Angular 22, Tailwind CSS 4, Angular Service Worker (PWA), Dexie.js (IndexedDB) |
| API | Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic |
| Banco | PostgreSQL em produção, SQLite no desenvolvimento e nos testes |
| Segurança | JWT de curta duração, refresh token em cookie HttpOnly, senhas com bcrypt |
| Testes | pytest (API) e Vitest (front-end) |
| CI | GitHub Actions |

## Estrutura

```
backend/   API FastAPI, migrações e testes
frontend/  aplicativo Angular (PWA)
.github/   pipeline de integração contínua
```

## Como rodar localmente

### API

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows
source .venv/bin/activate     # Linux/macOS
pip install -r requirements-dev.txt
cp .env.example .env          # ajuste DATABASE_URL e JWT_SECRET
alembic upgrade head
python -m app.cli create-user --name "Marta" --login marta --role owner
python -m app.cli seed-demo   # opcional: 110 clientes e 1000 lançamentos fictícios
uvicorn app.main:app --reload
```

### Front-end

```bash
cd frontend
npm install
npm start
```

O app abre em `http://localhost:4200` e usa o proxy `/api` para a API em `http://127.0.0.1:8000`.

## Testes

```bash
cd backend && pytest
cd frontend && npm test -- --watch=false
```

## Variáveis de ambiente da API

| Variável | Descrição |
| --- | --- |
| `DATABASE_URL` | URL do banco (ex.: `postgresql+psycopg://...`) |
| `JWT_SECRET` | segredo para assinar os tokens |
| `CORS_ORIGINS` | lista de origens permitidas |
| `SECURE_COOKIES` | `true` em produção (HTTPS) |
| `ENABLE_DOCS` | `false` em produção para esconder o `/docs` |
