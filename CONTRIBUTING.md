# Contributing to CAWA

## Development Setup

```bash
# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

## Running the Server Locally

```bash
# Copy and configure environment
cp .env_template .env
# Edit .env with your Cachet API URL and token

# Run the server
uv run start-adapter
```

Then go to http://127.0.0.1:8002

## Testing

```bash
uv run pytest
```

See [pytest documentation](https://docs.pytest.org/) for more options.

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting, enforced via pre-commit hooks.
See [pyproject.toml](pyproject.toml) for configuration.

## Setting up Cachet Locally

There's no dockerized Cachet available currently.
Follow the [Cachet Development Environment](https://docs.cachethq.io/v3.x/development) guide.
[Laravel Herd](https://herd.laravel.com/) is optional.

Note: The Cachet dev environment uses an in-memory SQLite database, so all data is lost when you stop the server.

## Integration Testing

For local integration testing with Prometheus and Alertmanager:

```bash
cd development_setup
docker compose up -d
```

This spawns:

- Blackbox exporter: http://localhost:9115/
- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093

The blackbox probe targets `localhost:9100`.
Start/stop a server there to trigger alerts:

```bash
# Start a server to resolve the alert
uv run python -m http.server 910{0|1|2}

# Stop (Ctrl+C) to trigger the alert
```
