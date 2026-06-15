# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project mostly adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://gitlab.heigit.org/heigit/utils/cachet-adapter/-/compare/71e885ba6adb146d8dd6cc32fcd1eb72ac5d084a...main)

### Added

- an adapter for Prometheus Alertmanager Webhook calls to be fed into Cachet with basic functionality
    - process alerts and forward to Cachet
    - record updates to alerts
    - provide a dependency tree for components to fail dependent components on central failures
    - synchronise the Cachet and Cachet adapter setup using config files
    - synchronise Cachet scheduled maintenances from a calendar