![GitHub release (latest by date)](https://img.shields.io/github/v/release/jsheputis/home-assistant-lifetime-fitness)
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/jsheputis)

# About

This integration uses [Life Time Fitness](https://www.lifetime.life)'s API in order to fetch multiple statistics and information on Life Time Fitness accounts.

# Installation

## 1. Easy Mode

Install via HACS.

## 2. Manual

Install it as you would do with any HomeAssistant custom component:

1. Download the `custom_components` folder from this repository.
1. Copy the `lifetime_fitness` directory within the `custom_components` directory of your HomeAssistant installation. The `custom_components` directory resides within the HomeAssistant configuration directory.
**Note**: if the custom_components directory does not exist, it needs to be created.
After a correct installation, the configuration directory should look like the following.
    ```
    └── ...
    └── configuration.yaml
    └── custom_components
        └── lifetime_fitness
            └── __init__.py
            └── api.py
            └── config_flow.py
            └── const.py
            └── manifest.json
            └── sensor.py
            └── strings.json
    ```

# Configuration

Once the component has been installed, you need to configure it by authenticating with a Life Time account. To do that, follow the following steps:
1. From the HomeAssistant web panel, navigate to 'Configuration' (on the sidebar) then 'Integrations'. Click `+` button in bottom right corner,
search '**Life Time Fitness**' and click 'Configure'.
1. Input your Life Time account username and password. Hit submit when selected.
1. You're done!

If you want to follow more than 1 account, just follow the same steps to add additional accounts.

## Usage

Every account configured will create a sensor, formatted as `sensor.<lifetime_username>_life_time_visits` (`<lifetime_username>` being the account username) with the following attributes:
* `visits_this_year` (a count of visits since January first this year)
* `visits_this_month` (a count of visits since the first day of this month)
* `visits_this_week` (a count of visits since the first day of the week, which is configured by integration options)
* `last_visit_timestamp` (a second-based timestamp of the last check-in)
