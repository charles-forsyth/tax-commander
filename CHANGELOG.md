# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-12-11
### Added
- **Package Structure:** Refactored entire codebase into a `src/tax_commander` layout.
- **Installer Support:** Added `pyproject.toml` for installation via `pip` or `uv`.
- **Global CLI:** The tool is now executable as `tax-commander` from anywhere.
- **Smart Config:** Application now searches for configuration in `~/.config/tax-commander/`, `~/.tax-commander.yaml`, and the current directory.
- **Bundled Schema:** Database schema is now packaged with the application for easier initialization.

### Changed
- Moved `simulation_run.sh` and dummy data generation to `tests/` directory.
- Updated all internal imports to relative imports for package compatibility.

### Security
- Added `.gitignore` to prevent sensitive data leaks.
- Moved sensitive `config.yaml` to `config.yaml.example`.

## [1.0.0] - 2025-11-27
### Initial Release
- Complete PA Act 48 compliant tax collection system.
- Feature: Audit-proof transaction logging.
- Feature: PDF Bill and Receipt generation.
- Feature: Monthly DCED Reporting.
- Feature: Supervisor Web Dashboard.
