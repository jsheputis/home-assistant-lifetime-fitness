# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0]

### Added

- **Reservations calendar** - New calendar entity showing upcoming reservations (classes, personal training, etc.)
  - Entity ID: `calendar.life_time_fitness_<username>_reservations`
  - Displays event name, location, instructor, and reservation type
  - Integrates with Home Assistant's calendar dashboard and automations
  - Fetches reservations for the next 30 days
- **Reservations API integration** - Fetches member reservations from the Life Time scheduling API (`/ux/web-schedules/v3/reservations`)
- **New calendar module** (`calendar.py`) - Calendar entity for displaying reservations

## [2.0.0]

### ⚠️ Breaking Changes

#### Sensor Architecture Overhaul

**Previous behavior (v1.x):** A single sensor (`sensor.<username>_life_time_visits`) with visit statistics stored as attributes.

**New behavior (v2.0):** Five separate sensor entities, each with its own state and history:

| New Sensor Entity | Description | Previous Equivalent |
|-------------------|-------------|---------------------|
| `sensor.life_time_fitness_<username>_total_visits` | Total visits (YTD) | Sensor state |
| `sensor.life_time_fitness_<username>_visits_this_year` | Visits since Jan 1 | `visits_this_year` attribute |
| `sensor.life_time_fitness_<username>_visits_this_month` | Visits since 1st of month | `visits_this_month` attribute |
| `sensor.life_time_fitness_<username>_visits_this_week` | Visits since week start | `visits_this_week` attribute |
| `sensor.life_time_fitness_<username>_last_visit` | Timestamp of last visit | `last_visit_timestamp` attribute |

#### Migration Required

After upgrading, you will need to:

1. **Update automations and scripts** that reference the old sensor entity ID or attributes
2. **Update dashboard cards** to use the new sensor entities
3. **Update template sensors** that extracted attribute values

**Example migration:**

```yaml
# Before (v1.x)
- platform: template
  sensors:
    gym_visits_this_month:
      value_template: "{{ state_attr('sensor.myemail_life_time_visits', 'visits_this_month') }}"

# After (v2.0) - No template needed, use the sensor directly
# sensor.life_time_fitness_myemail_visits_this_month
```

#### Benefits of New Architecture

- **Individual history tracking** - Each metric now has its own history graph
- **Long-term statistics** - Sensors with `state_class` support Home Assistant's long-term statistics
- **Better performance** - No need to parse attributes in templates
- **Proper device grouping** - All sensors grouped under a "Life Time Fitness" device in the UI

### Added

- **DataUpdateCoordinator pattern** - Centralized data fetching with better error handling and retry logic
- **Device registry support** - Account appears as a device with all sensors grouped underneath
- **Proper entity naming** - Uses Home Assistant's `has_entity_name` for consistent naming
- **State classes** - Sensors now support long-term statistics (`TOTAL` and `MEASUREMENT`)
- **Timestamp sensor** - Last visit is now a proper timestamp device class with datetime value
- **Comprehensive error handling** - Proper `ConfigEntryAuthFailed` and `ConfigEntryNotReady` exceptions
- **New coordinator module** (`coordinator.py`) - Handles all data processing and update coordination
- **Improved test coverage** - Tests for coordinator, sensors, API client, and config flow
- **Code quality tooling** - Added ruff, mypy, and pre-commit hooks
- **CONTRIBUTING.md** - Development guide for contributors

### Changed

- **Sensor base class** - Migrated from `Entity` to `SensorEntity`
- **Data processing** - Moved from sensor to coordinator for better separation of concerns
- **API client** - Improved error handling, proper Bearer token format, defensive JSON parsing
- **Options flow** - No longer requires full reload; updates coordinator settings directly

### Fixed

- **Null data handling** - Graceful handling of missing or malformed API responses
- **Error recovery** - `update_successful` flag properly reset on successful updates
- **Profile fetching** - Proper validation of API responses with meaningful error messages
- **Authentication errors** - All API exceptions properly mapped to Home Assistant exceptions

### Removed

- **Debug code** - Removed leftover `main()` test function from `api.py`
- **Legacy sensor attributes** - Visit statistics no longer stored as attributes

## [1.x.x] - Previous Releases

See [GitHub Releases](https://github.com/jsheputis/home-assistant-lifetime-fitness/releases) for previous release notes.
