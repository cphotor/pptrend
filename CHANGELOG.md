# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-13

### Added
- Initial release of `pptrend`.
- Zero-dependency CLI tool for tracking PyPI download trends.
- Adaptive ASCII charts (daily, weekly, monthly, yearly views).
- Local SQLite database storage with cross-platform support.
- Smart sync: checks local DB before fetching from PePy/PyPIStats APIs.
- Automatic cleanup of disconnected data (older than 180 days) during sync.
- `--clean` command to manually remove all stale records.
- `--version` (-V) and `--help` (-H) flags.
- MIT License and comprehensive documentation.
