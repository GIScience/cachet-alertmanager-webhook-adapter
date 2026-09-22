# <img src="resources/icon.png" width="5%"> Cachet-compatible Alertmanager Webhook Adapter (CAWA)

A webhook adapter that translates [Prometheus Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/)
alerts into [Cachet](https://cachethq.io/) status page incidents, and updates components.
It maintains a component dependency graph to automatically propagate status changes to dependent components.

> This is an independent, community-maintained project. It is not affiliated with, sponsored by, or endorsed by
> Cachet or Prometheus Alertmanager. See [TRADEMARK.md](TRADEMARK.md) for details on trademarks and endorsement.

<details>
<summary>Table of Contents</summary>
[[_TOC_]]
</details>

## Similar Projects

There are existing tools that basically do the same thing but are unmaintained,
and/or work only with the previous version of Cachet (v2):

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

| Variable           | Required | Default                 | Description                                                                 |
|--------------------|----------|-------------------------|-----------------------------------------------------------------------------|
| `CACHET_API_URL`   | Yes      | -                       | URL to your Cachet API (e.g., `https://status.example.com/api/v1`)          |
| `CACHET_TOKEN`     | Yes      | -                       | Bearer token for Cachet authentication                                      |
| `PORT`             | No       | `8002`                  | Server port                                                                 |
| `MESSAGE_OVERRIDE` | No       | `supplier`              | Whether to replace alert texts with generic ones: `all`, `supplier`, `none` |
| `LOG_LEVEL`        | No       | `INFO`                  | Log level                                                                   |
| `SQLITE_FILE`      | No       | `cachet_adapter.sqlite` | Path to the SQLite database file for storing mappings                       |

## Run

Now start the adapter using `docker compose up`.
Use the `-d` flag to start it in the background.

The adapter will be available at http://localhost:8002.
The full, interactive API documentation is served at http://localhost:8002/docs.

We suggest you use a `docker-compose.override.yml` file to adapt the compose file to your needs.

## Loading Data

Running the adapter on a bare setup works but is not very useful.
To quickly load your custom data, we provide helper scripts.

### load-components

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

Use `--prune` to delete any groups and components on Cachet that are not specified in the component file.
This brings Cachet fully in sync with the file. Note that renaming a group or component is treated as a deletion
and recreation, thereby losing existing linked incidents. To rename, do so manually in the Cachet UI instead.

### load-dependencies

It loads a list of dependencies into the adapter.

```shell
uv run load-dependencies <adapter-url> --graph-file /path/to/file.csv
```

The dependency file must have the format

```csv
from_group,from_component,to_group,to_component,relationship
<from_group>,<from_component>,<to_group>,<to_component>,<requires or optional>
```

Use `--prune` to delete any dependencies not specified in the file.
The adapter will then be fully in sync with the file.

### load-schedules

It loads scheduled maintenances from an ICS source (file or URL).

```shell
uv run load-schedules <adapter-url> --file /path/to/file.ics
# or
uv run load-schedules <adapter-url> --url https://example.com/calendar.ics
```

To link components to a maintenance event, put a JSON object into the event description that maps group names to
component names (same names as in `load-components`).

In your calendar, the description would then look something like
```
{"infrastructure":["Primary Database"]}
```
generating the following ICS
```ics
BEGIN:VEVENT
UID:3371b318-23a6-4621-b157-201e428c6e47
SUMMARY:Database upgrade
DESCRIPTION:{"infrastructure":["Primary Database"]}
DTSTART;TZID=Europe/Berlin:20260910T220000
DTEND;TZID=Europe/Berlin:20260910T235900
END:VEVENT
```
Note, that the description can contain no additional information apart from the linked components JSON.

Or you may simply use the keyword `[cachet:all]` to link every component.
In this case the description can be normal text and must only contain that set of characters at any point.

E.g. `We will update our services. Note for the system: [cachet:all]`

Use `--event-titles` to only import events with specific titles, and `--prune` to
delete schedules that are no longer in the calendar.

### sync-alerts

It pulls the current list of alerts from the Alertmanager and synchronises them with the CAWA.
This script is necessary
because [Alertmanager silences impact the webhook](https://gitlab.heigit.org/heigit/utils/cachet-adapter/-/work_items/19).
We suggest to run it in a cron-job e.g. every 30min.
It can also be used as a complete alternative to the webhook.

```shell
uv run sync-alerts <adapter-url> --alertmanager-url <alertmanager-url>
```

## How Alerts Become Incidents

When Alertmanager POSTs a webhook to `/adapt`, the adapter does the following for each alert:

1. determines the affected component from the alert labels,
2. walks the dependency graph to find all components that depend on it,
3. creates one Cachet incident linking all affected components, with statuses based on the alert severity and the
   dependency relationships.

Subsequent alerts with the same fingerprint and start time update the existing incident rather than creating
duplicates.
If neither the alerting component nor its dependent component exists in Cachet, no incident is created (unless a `force` flag is used).

### Alert Labels

| Label                   | Required | Description                                                                  |
|-------------------------|----------|------------------------------------------------------------------------------|
| `job`                   | Yes      | Component name (used to match Cachet component)                              |
| `cachet_group` or `org` | No       | Component group name (default: `''`, matches ungrouped components)           |
| `cachet_component`      | No       | Override `job` with a custom component name                                  |
| `cachet_incident_force` | No       | Create an incident even if no matching component exists (default: `false`)   |
| `severity`              | No       | Alert severity: `critical`, `error`, `warning`, `info` (default: `critical`) |

### Severity Mapping

| Alert Severity      | Cachet Component Status |
|---------------------|-------------------------|
| `critical`, `error` | Major Outage (4)        |
| `warning`, `info`   | Partial Outage (3)      |

| Alert State                     | Cachet Incident Status |
|---------------------------------|------------------------|
| `firing`                        | Reported               |
| `suppressed` (sync-alerts only) | Investigating          |
| `resolved`                      | Fixed                  |

### Incident Texts

The `MESSAGE_OVERRIDE` setting controls when an alert's own `title` and `summary`/`description` annotations are used,
instead of the generic ones supplied by the adapter.

- `all`: never, always use the generic texts
- `supplier` (default): only if the alerting component itself is on Cachet; unlisted ones
  (dependent components) keep the generic text
- `none`: always, whenever the annotations are present

## Component Dependency Graph

The adapter maintains a dependency graph that propagates status changes.
When a component fails, all components that depend on it are automatically linked to the incident.

- **Components** belong to **groups** (default: `''`, for ungrouped components)
- **Dependencies** are directional: "A depends on B" means A requires B
- **Relationship types**:
    - `requires`: Hard dependency. If B has a major outage, A gets major outage status.
    - `optional`: Soft dependency. If B fails, A gets partial outage status.

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

If `database` fails with a major outage, `api` and `web-app` also get major outage status (`requires` all the way).
If `cache` fails, `api` and `web-app` only get partial outage status.

Besides the [load-dependencies](#load-dependencies) script, the graph can be managed directly via the
`/component-mapping` endpoint (see http://localhost:8002/docs for details):

```bash
# Create or update a dependency
curl -X PUT "http://localhost:8002/component-mapping" \
  -H "Content-Type: application/json" \
  -d '{"from_component": "web-app", "to_component": "api", "relationship": "requires"}'

# Get all dependencies (including transitive) of web-app
curl "http://localhost:8002/component-mapping?group=general&component=web-app&recursive=true"

# Find all components that depend on database
curl "http://localhost:8002/component-mapping?component=database&upward=true"

# Delete a dependency
curl -X DELETE "http://localhost:8002/component-mapping?from_group=general&from_component=web-app&to_group=general&to_component=api"
```

Circular dependencies are detected and rejected with a 400 error.

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
    cachet_group: "infrastructure"
    cachet_component: "Primary Database"
    severity: critical
  annotations:
    title: "Database Connection Failed"
    description: "Cannot connect to the primary database."
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and code style guidelines.

## Trademarks & Endorsement

This project is not affiliated with, sponsored by, or endorsed by Cachet / CachetHQ or the
Prometheus / Alertmanager projects. "Cachet", "Prometheus", and "Alertmanager" are trademarks of
their respective owners and are used here only to describe interoperability. The project
[license](LICENSE) covers this repository's own source code and does not extend to those
third-party names or marks. See [TRADEMARK.md](TRADEMARK.md) for the full statement.

## Attribution

Icons by [Icons8](https://icons8.com)
