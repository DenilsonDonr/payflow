# PayFlow

A payment-processing backend built as a **modular monolith**. This is a learning project — the goal is to practice clean architecture and build things properly, not to ship a production product.

## Architecture

A single deployable, organized with hexagonal architecture and split by module — each with its own domain, application, and infrastructure layers. New capabilities are added as modules inside the same monolith, not as separate services.

## Stack

| Technology     | Version | Role                          |
|----------------|---------|-------------------------------|
| Python         | 3.12+   | Language                      |
| FastAPI        | 0.139+  | HTTP API                      |
| PostgreSQL     | 17      | Database                      |
| psycopg        | 3.3+    | PostgreSQL driver             |
| Alembic        | 1.18+   | Database migrations           |
| Docker Compose | —       | Local development database    |
| pytest         | 9.1+    | Tests                         |
| ruff + pyright | —       | Linting and strict type check |

## Development

Start the development database:

```bash
docker compose -f docker/development/compose.dev.yaml up -d
```

Run the tests:

```bash
uv run pytest
```
