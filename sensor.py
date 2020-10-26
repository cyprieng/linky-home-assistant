from datetime import timedelta, datetime
import json
import logging
import traceback

import requests
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ATTRIBUTION, ENERGY_KILO_WATT_HOUR, CURRENCY_EURO)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_time_interval, call_later

_LOGGER = logging.getLogger(__name__)

# CONST
DEFAULT_SCAN_INTERVAL = timedelta(hours=4)
CONF_COST = 'cost'
CONF_API_KEY = 'api-key'
CONF_POINT_ID = 'point-id'

HA_ATTRIBUTION = 'Data provided by Enedis'
HA_TIME = 'time'
HA_TIMESTAMP = 'timestamp'
HA_TYPE = 'type'

ICON_ELECTRICITY = 'lightning-bolt'
ICON_PRICE = 'mdi:currency-eur'

HA_LAST_ENERGY_KWH = 'Linky energy'
HA_LAST_ENERGY_PRICE = 'Linky energy price'
HA_MONTH_ENERGY_KWH = 'Linky energy month'
HA_MONTH_ENERGY_PRICE = 'Linky energy month price'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_KEY): cv.string,
    vol.Required(CONF_POINT_ID): cv.string,
    vol.Required(CONF_COST): cv.small_float,
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Configure the platform and add the Gazpar sensor."""

    _LOGGER.debug('Initializing Linky platform...')

    try:
        api_key = config[CONF_API_KEY]
        point_id = config[CONF_POINT_ID]
        cost = config[CONF_COST]

        account = LinkyAccount(hass, api_key, point_id, cost)
        add_entities(account.sensors, True)

        _LOGGER.debug('Linky platform initialization has completed successfully')
    except BaseException:
        _LOGGER.error('Linky platform initialization has failed with exception : {0}'.format(traceback.format_exc()))


class LinkyAccount:
    """Representation of a Linky account."""

    def __init__(self, hass, api_key, point_id, cost):
        """Initialise the Linky account."""
        self._api_key = api_key
        self._point_id = point_id
        self._cost = cost
        self.sensors = []

        call_later(hass, 5, self.update_linky_data)

        # Add sensors
        self.sensors.append(LinkySensor(HA_LAST_ENERGY_KWH, ENERGY_KILO_WATT_HOUR))
        self.sensors.append(LinkySensor(HA_LAST_ENERGY_PRICE, CURRENCY_EURO))
        self.sensors.append(LinkySensor(HA_MONTH_ENERGY_KWH, ENERGY_KILO_WATT_HOUR))
        self.sensors.append(LinkySensor(HA_MONTH_ENERGY_PRICE, CURRENCY_EURO))

        track_time_interval(hass, self.update_linky_data, DEFAULT_SCAN_INTERVAL)

    def update_linky_data(self, event_time):
        """Fetch new state data for the sensor."""

        _LOGGER.debug('Querying Linky library for new data...')

        try:
            # Get full month data
            data = requests.post('https://enedisgateway.tech/api', headers={
                'Authorization': self._api_key
            }, json={
                'type': 'consumption_load_curve',
                'usage_point_id': self._point_id,
                'start': datetime.now().replace(day=1).strftime('%d/%m/%Y'),
                'end': datetime.now().replace(day=31).strftime('%d/%m/%Y')
            }).json()
            _LOGGER.debug('data={0}'.format(json.dumps(data, indent=2)))

            # Group by day
            data_grouped = {}
            for d in data['meter_reading']['interval_reading']:
                date = d['date'][0:10]
                if date not in data_grouped:
                    data_grouped[date] = 0
                data_grouped[date] += d['value']

            last_kwh = int(data_grouped[max(data_grouped.keys())])
            month_kwh = sum([int(d) for _, d in data.items()])
            timestamp = datetime.strptime(max(data_grouped.keys()), '%d/%m/%Y')

            # Update sensors
            for sensor in self.sensors:
                if sensor.name == HA_LAST_ENERGY_KWH:
                    sensor.set_data(timestamp, last_kwh)
                if sensor.name == HA_MONTH_ENERGY_KWH:
                    sensor.set_data(timestamp, month_kwh)
                if sensor.name == HA_LAST_ENERGY_PRICE:
                    sensor.set_data(timestamp, round(last_kwh * self._cost, 4))
                if sensor.name == HA_MONTH_ENERGY_PRICE:
                    sensor.set_data(timestamp, round(month_kwh * self._cost, 4))

                sensor.async_schedule_update_ha_state(True)
                _LOGGER.debug('HA notified that new data is available')
        except BaseException:
            _LOGGER.error('Failed to query Linky library with exception : {0}'.format(traceback.format_exc()))


class LinkySensor(Entity):
    """Representation of a sensor entity for Linky."""

    def __init__(self, name, unit):
        """Initialize the sensor."""
        self._name = name
        self._unit = unit
        self._timestamp = None
        self._measure = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._measure

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def icon(self):
        """Return the icon of the sensor."""
        if self._name in [HA_MONTH_ENERGY_KWH, HA_LAST_ENERGY_KWH]:
            return ICON_ELECTRICITY
        else:
            return ICON_PRICE

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            ATTR_ATTRIBUTION: HA_ATTRIBUTION,
            HA_TIMESTAMP: self._timestamp,
        }

    def set_data(self, timestamp, measure):
        """Update sensor data"""
        self._measure = measure
        self._timestamp = timestamp
