# Rhandir 🧭

> **Daemon e coletor leve e assíncrono para ingestão, rastreamento e busca de dados para alimentar um sistema de Segundo Cérebro no Obsidian (ecossistema `mindon`).**

O `rhandir` opera como o coletor mecânico de baixo nível ("Pasta Máquina"). Ele captura dados brutos (metadados e transcrições do YouTube), deduplica via PostgreSQL em modo WAL, e grava notas estruturadas em Markdown na pasta de entrada do Obsidian sem realizar síntese analítica pesada localmente.

Projetado sob os princípios de **Clean Architecture**, **TDD/BDD**, **Clean Code** e **The Pragmatic Programmer**, otimizado para ambientes com restrições de hardware (Intel Core i7 2ª geração, 8GB RAM, Ubuntu 24.04 no WSL2).

---

## 🛠️ Requisitos Técnicos

- **Python:** `>= 3.12`
- **Gerenciador de Pacotes:** `uv` (`>= 0.13`)
- **Banco de Dados:** PostgreSQL (modo WAL com tabela leve e índices)
- **Obsidian Vault:** Pasta de entrada configurada (`OBSIDIAN_RAW_DIR`)

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
- `DATABASE_URL`: String de conexão com o PostgreSQL (`postgresql://user:pass@localhost:5432/rhandir`).
- `OBSIDIAN_RAW_DIR`: Diretório absoluto da "Pasta Máquina" no Obsidian (ex: `/home/user/obsidian/mindon/00_Inbox/Raw_Machine`).
- `TAKEOUT_INBOX_DIR`: Diretório monitorado onde arquivos `watch-history.json` do Google Takeout são depositados (`inbox/takeout`).

---

## 💻 Comandos da CLI (`rhandir`)

O comando `rhandir` está configurado diretamente no ambiente virtual via `uv`:

```bash
# 1. Consultar a saúde e contagem de vídeos por status no PostgreSQL
uv run rhandir status

# 2. Executar um ciclo manual de sincronização sob demanda
uv run rhandir sync youtube

# 3. Executar o daemon contínuo em primeiro plano (foreground)
uv run rhandir run
```

---

## 🧪 Testes Automatizados e Qualidade de Código

O projeto segue rigorosamente o ciclo Red-Green-Refactor (TDD) com 100% de isolamento de rede:

```bash
# Executar a suíte de testes unitários e de integração
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
│   ├── application/                  # Camada 2: Casos de Uso
│   │   ├── use_cases/                # IngestYouTubeVideoUseCase, IngestYouTubeHistoryUseCase
│   │   ├── dtos/video_dto.py         # IngestionSummaryDTO
│   │   └── services/                 # CircuitBreaker com Rate Limiter e Jitter
│   ├── interfaces/                   # Camada 3: Adaptadores de Interface
│   │   ├── controllers/daemon.py     # Controlador do loop com shutdown gracioso
│   │   └── presenters/               # MarkdownPresenter para Obsidian
│   ├── infrastructure/               # Camada 4: Infraestrutura & Drivers
│   │   ├── config/settings.py        # Configurações tipadas via pydantic-settings
│   │   ├── db/                       # PostgreSQL asyncpg e PostgresIngestionRepository
│   │   ├── external/                 # TakeoutParser, TakeoutCollector, YouTubeTranscriptProvider
│   │   └── filesystem/               # VaultWriter assíncrono e atômico (aiofiles)
│   └── cli/app.py                    # Entrypoint CLI Typer (status, sync, run)
├── systemd/
│   └── rhandir.service               # Unidade de serviço systemd para WSL2
└── tests/                            # Testes unitários e de integração (100% mockados)
```
