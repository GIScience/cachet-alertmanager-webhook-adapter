# Cachet Adapter

This is an API adapter that serves as a web-hook target for Prometheus' Alertmanager and then creates and
updates cachet incidents and components from it.
It includes a component dependency graph functionality to link components to incidents.

Install the tool using `uv sync`.

Copy the `.env_template` to `.env` and fill it with the required settings: `cp .env_template .env`.

Run the api using `uv run src/cachet_adapter/api.py ` then go to http://127.0.0.1:8000

## Similar Services

There are existing tools that basically do the same thing but are >5y unmaintained:

- https://github.com/gregdhill/prometheus-cachet
- https://github.com/oxyno-zeta/prometheus-cachethq

You can also follow the discussion on the topic at https://github.com/cachethq/core/issues/310 .

# Development

Run `uv run pre-commit install` to activate pre-commit hooks locally.

For integration testing, go to [development_setup](development_setup) and run:

`docker compose up -d`

This will spawn a prometheus and alertmanager locally that is constantly firing and that you can reach
at http://localhost:9115/, http://localhost:9090 and http://localhost:9093 respectively.

The blackbox test is targeting localhost:9100 so you can start and stop a service there like
`uv run python -m http.server 910{0|1|2}`.

You can now use the API to link components and see the effect.
As of today there is no dockerised cachet available but setting up
the [Development Environment](https://docs.cachethq.io/v3.x/development) is quite straight forward.
Herd is optional there.