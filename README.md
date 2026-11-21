# Rhandir 🧭

> **Daemon e coletor leve e assíncrono para ingestão, rastreamento e busca de dados para alimentar um sistema de Segundo Cérebro no Obsidian (ecossistema `mindon`).**

O `rhandir` opera como o coletor mecânico de baixo nível ("Pasta Máquina"). Ele captura dados brutos (metadados e transcrições do YouTube via Takeout ou via Telegram Bot), deduplica via PostgreSQL em modo WAL, e grava notas estruturadas em Markdown na pasta de entrada do Obsidian sem realizar síntese analítica pesada localmente.

Projetado sob os princípios de **Clean Architecture**, **TDD/BDD**, **Clean Code** e **The Pragmatic Programmer**, otimizado para ambientes com restrições de hardware (Intel Core i7 2ª geração, 8GB RAM, Ubuntu 24.04 no WSL2).

---

## 🛠️ Requisitos Técnicos

- **Python:** `>= 3.12`
- **Gerenciador de Pacotes:** `uv` (`>= 0.13`)
- **Docker & Docker Compose:** Para execução do container PostgreSQL 16
- **Rclone:** Para sincronização do cofre Obsidian (`data/vault`) com o Google Drive
- **Obsidian Vault:** Pasta de entrada configurada (`OBSIDIAN_RAW_DIR`)
- **Telegram Bot (Opcional):** Token do bot criado via `@BotFather`

---

## 🚀 Como Iniciar Localmente

### 1. Clonar e Instalar Dependências
```bash
git clone <repo-url> rhandir
cd rhandir

# Sincronizar o ambiente virtual e dependências via uv
uv sync
```

### 2. Configurar Variáveis de Ambiente
Copie o arquivo de exemplo e ajuste os caminhos para o seu ambiente:
```bash
cp .env.example .env
```

Parâmetros principais no `.env`:
- `DATABASE_URL`: String de conexão com o PostgreSQL (`postgresql://postgres:postgres@localhost:5432/rhandir`).
- `OBSIDIAN_RAW_DIR`: Diretório absoluto da "Pasta Máquina" no Obsidian (ex: `/home/user/prod/rhandir/data/vault/00_Inbox/Raw_Machine`).
- `RCLONE_VAULT_REMOTE`: Caminho remoto configurado no rclone para o cofre no Google Drive (ex: `gdrive:Obsidian`).
- `TAKEOUT_INBOX_DIR`: Diretório monitorado onde arquivos de histórico do Takeout são depositados (`data/takeout`).
- `TELEGRAM_BOT_TOKEN`: Token do bot do Telegram (se preenchido, o daemon escutará mensagens ativamente).
- `TELEGRAM_ALLOWED_CHAT_IDS`: Lista em formato JSON com chat IDs autorizados (ex: `[123456789]`). Se vazio, aceita qualquer chat.

### 3. Iniciar o Banco de Dados PostgreSQL (Docker)
Inicie o container PostgreSQL configurado com persistência no diretório `data/br`:
```bash
docker compose up -d

# Validar a conexão e integridade da base
uv run rhandir status
```

### 4. Sincronizar o Obsidian Vault com o Google Drive (Rclone)
```bash
# Baixar o cofre do Google Drive para o diretório local (data/vault):
uv run rhandir sync vault --direction pull

# Ou enviar alterações locais para a nuvem:
uv run rhandir sync vault --direction push
```

---

## 📱 Ingestão via Telegram Bot

Quando `TELEGRAM_BOT_TOKEN` estiver configurado no `.env`, o daemon (`uv run rhandir run`) iniciará o `TelegramListener`:

1. Envie qualquer link de vídeo do YouTube para o seu bot (formatos suportados: `https://youtube.com/watch?v=...`, `https://youtu.be/...`, shorts, lives ou links com parâmetros extras).
2. O bot valida a autorização do seu chat.
3. Notifica que está processando o vídeo.
4. Baixa e limpa a transcrição, formatando o arquivo `.md` na Pasta Máquina do Obsidian.
5. Responde no Telegram confirmando a gravação com o caminho do arquivo gerado no vault.

---

## 💻 Comandos da CLI (`rhandir`)

O comando `rhandir` está configurado diretamente no ambiente virtual via `uv`:

```bash
# 1. Consultar a saúde e contagem de vídeos por status no PostgreSQL
uv run rhandir status

# 2. Sincronizar o Obsidian Vault com o Google Drive via rclone
uv run rhandir sync vault --direction pull   # ou --direction push

# 3. Executar um ciclo manual de sincronização sob demanda (Takeout)
uv run rhandir sync youtube

# 4. Executar o daemon contínuo em primeiro plano (foreground: Takeout polling + Telegram Bot)
uv run rhandir run
```

---

## 🧪 Testes Automatizados e Qualidade de Código

O projeto segue rigorosamente o ciclo Red-Green-Refactor (TDD) com 100% de isolamento de rede:

```bash
# Executar a suíte completa de testes
uv run pytest

# Executar com relatório de cobertura detalhado
uv run pytest --cov=rhandir --cov-report=term-missing

# Verificar linters e estilo de código com Ruff
uv run ruff check .

# Formatar o código
uv run ruff format .
```

---

## 📁 Estrutura Arquitetural (Clean Architecture)

```
rhandir/
├── AGENTS.md                         # Diretrizes mestras e governança do agente
├── pyproject.toml                    # Configuração de dependências e ferramentas via uv
├── .env.example                      # Modelo documentado de variáveis de ambiente
├── src/rhandir/
│   ├── core/                         # Camada 1: Domínio Puro
│   │   ├── domain/
│   │   │   ├── entities/video.py     # Entidades Video e IngestionRecord
│   │   │   ├── value_objects/        # Value Objects VideoId e IngestionStatus
│   │   │   └── exceptions.py         # Exceções de Domínio puras
│   │   └── ports/                    # Interfaces Abstratas (Protocols)
│   │       ├── collectors.py         # IHistoryCollector
│   │       ├── listeners.py          # IMessageListener
│   │       ├── repositories.py       # IIngestionRepository
│   │       ├── transcripts.py        # ITranscriptProvider
│   │       └── writers.py            # IVaultWriter
│   ├── application/                  # Camada 2: Casos de Uso
│   │   ├── use_cases/                # IngestYouTubeVideoUseCase, IngestYouTubeHistoryUseCase
│   │   ├── dtos/video_dto.py         # IngestionSummaryDTO
│   │   └── services/                 # CircuitBreaker com Rate Limiter e Jitter
│   ├── interfaces/                   # Camada 3: Adaptadores de Interface
│   │   ├── controllers/daemon.py     # Controlador do loop com shutdown gracioso e listeners
│   │   └── presenters/               # MarkdownPresenter para Obsidian
│   ├── infrastructure/               # Camada 4: Infraestrutura & Drivers
│   │   ├── config/settings.py        # Configurações tipadas via pydantic-settings
│   │   ├── db/                       # PostgreSQL asyncpg e PostgresIngestionRepository
│   │   ├── external/                 # TakeoutParser, TelegramListener, YouTubeTranscriptProvider
│   │   └── filesystem/               # VaultWriter assíncrono e atômico (aiofiles)
│   └── cli/app.py                    # Entrypoint CLI Typer (status, sync, run)
├── systemd/
│   └── rhandir.service               # Unidade de serviço systemd para WSL2
└── tests/                            # Testes unitários e de integração (100% mockados)
```
