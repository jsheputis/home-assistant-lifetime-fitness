![GitHub release (latest by date)](https://img.shields.io/github/v/release/jsheputis/home-assistant-lifetime-fitness)
![GitLeaks](https://img.shields.io/badge/protected%20by-gitleaks-blue)

# About

This integration uses [Life Time Fitness](https://www.lifetime.life)'s API to fetch visit statistics and information for Life Time Fitness accounts.

## Features

- Track total gym visits (year-to-date)
- Monitor visits this year, month, and week
- View last visit timestamp
- Support for multiple accounts
- Configurable week start day

# Installation

## 1. Easy Mode (HACS)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

1. Open HACS Settings and add this repository (https://github.com/jsheputis/home-assistant-lifetime-fitness/)
   as a Custom Repository (use **Integration** as the category).
2. The `Life Time Fitness` page should automatically load (or find it in the HACS Store)
3. Click `Download`
4. Continue to [Configuration](#configuration)

## 2. Manual Installation

Install it as you would do with any Home Assistant custom component:

1. Download the `custom_components` folder from this repository.
2. Copy the `lifetime_fitness` directory within the `custom_components` directory of your Home Assistant installation. The `custom_components` directory resides within the Home Assistant configuration directory.

**Note**: If the custom_components directory does not exist, it needs to be created.

After a correct installation, the configuration directory should look like the following:

```text
└── ...
└── configuration.yaml
└── custom_components
    └── lifetime_fitness
        └── __init__.py
        └── api.py
        └── config_flow.py
        └── const.py
        └── coordinator.py
        └── manifest.json
        └── model.py
        └── sensor.py
        └── strings.json
        └── translations/
```

# Configuration

Once the component has been installed, you need to configure it by authenticating with a Life Time account:

1. From the Home Assistant web panel, navigate to **Settings** → **Devices & Services** → **Integrations**
2. Click the `+ Add Integration` button in the bottom right corner
3. Search for **Life Time Fitness** and select it
4. Enter your Life Time account username and password, then click Submit
5. *(Optional)* After configuration, you can change the starting day of week by clicking **Configure** on the integration

To track multiple accounts, repeat these steps for each account.

# Usage

## Sensors

Each configured account creates a **device** named "Life Time Fitness (username)" with five sensor entities:

| Sensor | Entity ID | Description |
|--------|-----------|-------------|
| **Total visits** | `sensor.life_time_fitness_<username>_total_visits` | Total visits year-to-date |
| **Visits this year** | `sensor.life_time_fitness_<username>_visits_this_year` | Visits since January 1st |
| **Visits this month** | `sensor.life_time_fitness_<username>_visits_this_month` | Visits since the 1st of the current month |
| **Visits this week** | `sensor.life_time_fitness_<username>_visits_this_week` | Visits since the configured week start day |
| **Last visit** | `sensor.life_time_fitness_<username>_last_visit` | Timestamp of your most recent check-in |

### Sensor Details

- **Total visits**, **Visits this year/month/week** - Integer values with unit "visits"
- **Last visit** - A timestamp sensor showing the date/time of your last gym visit

All visit count sensors support Home Assistant's long-term statistics, allowing you to track trends over time.

## Example Automations

### Notify if you haven't been to the gym this week

```yaml
automation:
  - alias: "Gym Reminder"
    trigger:
      - platform: time
        at: "18:00:00"
    condition:
      - condition: state
        entity_id: sensor.life_time_fitness_myemail_visits_this_week
        state: "0"
      - condition: time
        weekday:
          - fri
    action:
      - service: notify.mobile_app
        data:
          message: "You haven't been to the gym this week!"
```

### Track monthly gym visits in a dashboard

```yaml
type: entities
entities:
  - entity: sensor.life_time_fitness_myemail_total_visits
    name: Total Visits (YTD)
  - entity: sensor.life_time_fitness_myemail_visits_this_month
    name: This Month
  - entity: sensor.life_time_fitness_myemail_visits_this_week
    name: This Week
  - entity: sensor.life_time_fitness_myemail_last_visit
    name: Last Visit
```

# Upgrading from v1.x

## ⚠️ Breaking Changes in v2.0

Version 2.0 introduces a significant change to how sensors are structured. **This is a breaking change** that will require updates to your automations, scripts, and dashboards.

### What Changed

**Before (v1.x):** One sensor with visit data stored as attributes

```yaml
# Old sensor
sensor.myemail_life_time_visits
  state: 45  # total visits
  attributes:
    visits_this_year: 45
    visits_this_month: 8
    visits_this_week: 2
    last_visit_timestamp: 1701561600
```

**After (v2.0):** Five separate sensors, each with its own state and history

```yaml
# New sensors
sensor.life_time_fitness_myemail_total_visits: 45
sensor.life_time_fitness_myemail_visits_this_year: 45
sensor.life_time_fitness_myemail_visits_this_month: 8
sensor.life_time_fitness_myemail_visits_this_week: 2
sensor.life_time_fitness_myemail_last_visit: 2023-12-03T00:00:00+00:00
```

### Migration Guide

#### Update Automations

```yaml
# Before
- condition: numeric_state
  entity_id: sensor.myemail_life_time_visits
  attribute: visits_this_week
  below: 1

# After
- condition: numeric_state
  entity_id: sensor.life_time_fitness_myemail_visits_this_week
  below: 1
```

#### Update Templates

```yaml
# Before
{{ state_attr('sensor.myemail_life_time_visits', 'visits_this_month') }}

# After
{{ states('sensor.life_time_fitness_myemail_visits_this_month') }}
```

#### Update Dashboard Cards

Replace attribute references with the new sensor entities directly.

### Benefits of the New Architecture

- **Individual history** - Each metric has its own history graph in Home Assistant
- **Long-term statistics** - Track trends over weeks and months
- **Better performance** - No template parsing needed
- **Device grouping** - All sensors organized under one device in the UI
- **Proper timestamps** - Last visit is now a real timestamp sensor

See [CHANGELOG.md](CHANGELOG.md) for complete release notes.

# Troubleshooting

## Common Issues

### "Invalid authentication" error

- Verify your username and password are correct
- Try logging in at [my.lifetime.life](https://my.lifetime.life) to confirm your credentials work
- If you have multiple accounts with the same email, try using your member number instead

### "Too many authentication attempts"

- Your account may be temporarily locked due to failed login attempts
- Wait 15-30 minutes before trying again

### Sensors showing "unavailable"

- Check your Home Assistant logs for error messages
- The Life Time API may be temporarily unavailable
- Try reloading the integration from Settings → Devices & Services

## Debug Logging

To enable debug logging, add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.lifetime_fitness: debug
```

# Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

# License

This project is licensed under the MIT License.
