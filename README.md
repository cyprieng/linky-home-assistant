# Linky home assistant

This module show your Linky consumption inside home assistant:
![Linky home assistant](https://user-images.githubusercontent.com/2521188/99240519-e4df1880-27fc-11eb-9a73-ab39de649f9e.png)

It uses [https://enedisgateway.tech/](https://enedisgateway.tech/) to retrieve linky data.


## Install

### HACS (recommended)

You can install this custom component using [HACS](https://hacs.xyz/) by adding a custom repository.

### Manual install

Copy this repository inside `config/custom_components/linky`.

## Configuration

Retrieve you api key and point id from [https://enedisgateway.tech/](https://enedisgateway.tech/). 

Add this to your `configuration.yaml`:

```yaml
sensor:
  - platform: linky
    api_key: !secret linky.api_key
    point_id: !secret linky.point_id
    cost: 0.1557  # Cost per kWh
```

This will create 4 sensors:
* last day kWh
* last day EUR
* current month kWh
* current month EUR
