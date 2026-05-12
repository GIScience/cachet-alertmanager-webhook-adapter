# Cachet Alertmanager Webhook Adapter (CAWA)

A webhook adapter that translates [Prometheus Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/)
alerts into [Cachet](https://cachethq.io/) status page incidents, and updates components.
It maintains a component dependency graph to automatically propagate status changes to dependent components.

[[_TOC_]]

## Similar Projects

There are existing tools that basically do the same thing but are >5y unmaintained:

- https://github.com/gregdhill/prometheus-cachet
- https://github.com/oxyno-zeta/prometheus-cachethq

You can also follow the discussion on the topic at https://github.com/cachethq/core/issues/310

## Installation

If you do not need a development setup (see [Contributing](#contributing)) the easiest way to run the adapter is the
dockerised version.
Run `docker compose build` to build the docker image locally.

### Configuration

Copy the `.env_template` to `.env` by running `cp .env_template .env`.
Then fill in the required parameters.

The adapter has the following environment variables:

| Variable         | Required | Default                 | Description                                                        |
|------------------|----------|-------------------------|--------------------------------------------------------------------|
| `CACHET_API_URL` | Yes      | -                       | URL to your Cachet API (e.g., `https://status.example.com/api/v1`) |
| `CACHET_TOKEN`   | Yes      | -                       | Bearer token for Cachet authentication                             |
| `PORT`           | No       | `8002`                  | Server port                                                        |
| `SQLITE_FILE`    | No       | `cachet_adapter.sqlite` | Path to the SQLite database file for storing mappings              |

#### Setup

Running the adapter on a bare setup works but is not very useful.
To quickly load your custom data, we provide a helper script: `load-components`.

It reads in a JSON file and creates the specified components in Cachet.

```shell
uv run load-components --component-file /path/to/file.json
```

The component file must have the format

```json
{
  "<group name>": [
    {
      "name": "<component name>",
      "description": "<optional description>",
      "link": "<optional link>"
    }
  ]
}
```

## Run

Now start the adapter using `docker compose up`.
Use the `-d` flag to start it in the background.

The adapter will be available at http://localhost:8002/docs.

We suggest you use a `docker-compose.override.yml` file to adapt the compose file to your needs.

---

## API Reference

### Alert Webhook Endpoint

```http
POST /adapt
```

Receives Alertmanager webhook payloads and creates/updates Cachet incidents.

#### Request Body

```json
{
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "job": "my-service",
        "severity": "critical"
      },
      "annotations": {
        "title": "Service Unavailable",
        "description": "The service is not responding to health checks."
      },
      "startsAt": "2025-01-27T10:30:00Z",
      "fingerprint": "abc123unique"
    }
  ]
}
```

#### Alert Labels

| Label              | Required | Description                                                                  |
|--------------------|----------|------------------------------------------------------------------------------|
| `job`              | Yes      | Component name (used to match Cachet component)                              |
| `cachet_component` | No       | Override `job` with a custom component name                                  |
| `severity`         | No       | Alert severity: `critical`, `error`, `warning`, `info` (default: `critical`) |
| `org`              | No       | Component group name (default: `''`, matches ungrouped components)           |

#### Severity Mapping

| Alert Severity      | Cachet Component Status |
|---------------------|-------------------------|
| `critical`, `error` | Major Outage (4)        |
| `warning`, `info`   | Partial Outage (3)      |

#### Response

```json
{
  "incident_ids": [
    42,
    43
  ]
}
```

---

## Component Dependency Graph

The adapter maintains a dependency graph that propagates status changes.
When a component fails, all components that depend on it are automatically linked to the incident.

### Concepts

- **Components** belong to **groups** (default: `''`, for ungrouped components)
- **Dependencies** are directional: "A depends on B" means A requires B
- **Relationship types**:
    - `requires`: Hard dependency. If B has a major outage, A gets major outage status.
    - `optional`: Soft dependency. If B fails, A gets partial outage status.

### Example Dependency Graph

```
┌─────────┐     requires     ┌─────────┐     optional     ┌───────┐
│ web-app │ ────────────────►│   api   │ ───────────────► │ cache │
└─────────┘                  └─────────┘                  └───────┘
                                  │
                             requires
                                  │
                                  ▼
                            ┌──────────┐
                            │ database │
                            └──────────┘
```

**Scenario 1: `database` fails (Major Outage)**

- `database` → Major Outage
- `api` → Major Outage (requires database)
- `web-app` → Major Outage (requires api)

**Scenario 2: `cache` fails (Major Outage)**

- `cache` → Major Outage
- `api` → Partial Outage (optional dependency on cache)
- `web-app` → Partial Outage (transitive through api)

---

## Managing Dependencies

### Create or Update a Dependency

```http
PUT /component-mapping
Content-Type: application/json

{
  "from_component": "web-app",
  "to_component": "api",
  "relationship": "requires"
}
```

Optional fields:

- `from_group`: Source component group (default: `''`)
- `to_group`: Target component group (default: `''`)

**Response:** Returns all dependencies of the `from_component`.

```json
[
  {
    "from_group": "general",
    "from_component": "web-app",
    "to_group": "general",
    "to_component": "api",
    "relationship": "requires"
  }
]
```

**Note:** Circular dependencies are detected and rejected with a 400 error.

---

### Query Dependencies

```http
GET /component-mapping
```

**Query Parameters:**

| Parameter   | Type   | Description                                                       |
|-------------|--------|-------------------------------------------------------------------|
| `group`     | string | Filter by source group                                            |
| `component` | string | Filter by source component                                        |
| `recursive` | bool   | Include transitive dependencies                                   |
| `upward`    | bool   | Query reverse direction (find dependents instead of dependencies) |

**Examples:**

```bash
# Get all dependency mappings
curl "http://localhost:8002/component-mapping"

# Get direct dependencies of web-app
curl "http://localhost:8002/component-mapping?group=general&component=web-app"

# Get all dependencies (including transitive) of web-app
curl "http://localhost:8002/component-mapping?group=general&component=web-app&recursive=true"

# Find all components that depend on database
curl "http://localhost:8002/component-mapping?component=database&upward=true"

# Find all components that depend on database (including transitive dependents)
curl "http://localhost:8002/component-mapping?group=general&component=database&recursive=true&upward=true"
```

**Response with `recursive=true`:**

```json
[
  {
    "from_group": "general",
    "from_component": "web-app",
    "to_group": "general",
    "to_component": "api",
    "relationship": "requires",
    "transitive": false
  },
  {
    "from_group": "general",
    "from_component": "web-app",
    "to_group": "general",
    "to_component": "database",
    "relationship": "requires",
    "transitive": true
  }
]
```

---

### Delete a Dependency

```http
DELETE /component-mapping?from_group=general&from_component=web-app&to_group=general&to_component=api
```

**Response:** Returns remaining dependencies of the `from_component`.

---

## Alertmanager Configuration

Configure Alertmanager to send webhooks to the adapter:

```yaml
# alertmanager.yml
receivers:
  - name: 'cachet'
    webhook_configs:
      - url: 'http://127.0.0.1:8002/adapt'
        send_resolved: true

route:
  receiver: 'cachet'
  group_by: [ 'alertname', 'job' ]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

### Alert Rule Example

```yaml
# prometheus/rules/alerts.yml
groups:
  - name: service-alerts
    rules:
      - alert: ServiceDown
        expr: up{job="my-service"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          title: "Service {{ $labels.job }} is down"
          description: "{{ $labels.job }} has been down for more than 1 minute."
```

### Using Custom Component Names

If your Prometheus job names don't match Cachet component names, use the `cachet_component` label:

```yaml
- alert: DatabaseConnectionFailed
  expr: db_connections == 0
  labels:
    job: "postgres-exporter"
    cachet_component: "Primary Database"
    severity: critical
    org: "infrastructure"
  annotations:
    title: "Database Connection Failed"
    description: "Cannot connect to the primary database."
```

---

## How It Works

1. **Alert received**: Alertmanager POSTs a webhook to `/adapt`
2. **Dependency resolution**: Walks the dependency graph upward to find all components that depend on the alerting
   component
3. **Component lookup**: Looks up the alerting component and all dependent components in Cachet
4. **Status calculation**: Applies relationship rules to determine each component's status
5. **Incident creation/update**: Creates a new incident or updates existing (tracked by alert fingerprint)

### Incident Lifecycle

- **Alert fires** (`status: "firing"`) → Creates incident with status `REPORTED`
- **Alert resolves** (`status: "resolved"`) → Updates incident to status `FIXED`

The adapter tracks alert fingerprints to incident IDs, so subsequent alerts with the same fingerprint update the
existing incident rather than creating duplicates.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and code style guidelines.
