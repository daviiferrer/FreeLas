# 🤖 FreeLaas — AI Freelancing Agent

Sistema autônomo de prospecção e geração de propostas para freelancers na plataforma **99Freelas**.

## O que faz?

1. **Scraper** — Monitora projetos novos na categoria configurada (ex: Web, Mobile e Software)
2. **Scanner (IA)** — Filtra projetos usando o sistema HACRB, rejeitando o que não se encaixa no perfil
3. **Analyst (IA)** — Classifica o cliente em arquétipos e avalia complexidade
4. **Strategist (IA)** — Gera proposta personalizada usando 4 frameworks (PSC, Investigativa, Consultiva, Curta)
5. **Notificação (WhatsApp)** — Envia a proposta pronta para um grupo no WhatsApp via WAHA
6. **Aprovação Humana** — Você decide aprovar ou rejeitar pelo WhatsApp

## Stack

| Serviço | Tecnologia |
|---------|-----------|
| Backend | Python 3.11 + FastAPI + APScheduler |
| IA | Qwen (Alibaba Cloud) — 3 modelos especializados |
| Database | PostgreSQL 16 |
| WhatsApp | WAHA Plus (API REST) |
| Automação | Playwright (submit proposals) |
| Deploy | Docker Compose |

## Setup Local

```bash
# 1. Clone
git clone https://github.com/daviiferrer/FreeLas.git
cd FreeLas

# 2. Configure
cp .env.example .env
# edite o .env com suas chaves

# 3. Suba
docker compose up -d --build

# 4. Verifique
docker compose logs -f app
```

## Deploy em VPS

```bash
# Na VPS:
git clone https://github.com/daviiferrer/FreeLas.git /opt/freelaas
cd /opt/freelaas
cp .env.example .env
nano .env  # preencha com valores reais
docker compose up -d --build
```

## Estrutura

```
app/
├── ai/           # Prompts e agentes IA (scanner, analyst, strategist)
├── api/          # Webhooks (WAHA)
├── models/       # SQLAlchemy models
├── pipeline/     # Orchestrator (ciclo completo)
├── scraper/      # Client HTTP + parser HTML
├── services/     # WAHA client, memory service
├── automator/    # Playwright (submit proposals)
└── config.py     # Settings (Pydantic)
```

## Variáveis de Ambiente

Veja `.env.example` para referência completa.

## Licença

Privado — Davi Ferrer © 2026
