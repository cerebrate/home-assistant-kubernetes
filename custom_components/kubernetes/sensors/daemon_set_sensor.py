"""Platform for deployment sensor integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.components.sensor import ENTITY_ID_FORMAT, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import config_validation as cv, entity_platform

from ..kubernetes_entity import KubernetesEntity
from ..const import (
    DOMAIN,
    ICON_DAEMONSET_NOTOK,
    ICON_DAEMONSET_OK,
    SERVICE_SET_IMAGE_DAEMONSET,
    PARAM_CONTAINER,
    PARAM_IMAGE,
    KUBERNETES_KIND_DAEMONSET,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    platform = entity_platform.async_get_current_platform()

    hub = hass.data[DOMAIN][entry.entry_id]

    await hub.async_start_listener(
        async_add_entities, hub.list_daemon_sets_func(), DaemonSetSensor
    )

    platform.async_register_entity_service(
        SERVICE_SET_IMAGE_DAEMONSET,
        {
            vol.Required(PARAM_CONTAINER): cv.string,
            vol.Required(PARAM_IMAGE): cv.string,
        },
        "set_image",
    )


class DaemonSetSensor(KubernetesEntity, SensorEntity):
    def __init__(self, hub, data):
        super().__init__(hub, data, ENTITY_ID_FORMAT)

    @property
    def state(self) -> str:
        return self.is_ok()

    @staticmethod
    def kind() -> str:
        return KUBERNETES_KIND_DAEMONSET

    async def set_image(self, container: str, image: str) -> None:
        await self.hub.set_image(
            self,
            container,
            image,
        )

    def is_ok(self) -> bool:
        status = self.getData().status
        cps = status.current_number_scheduled
        pa = status.number_available

        return (pa == cps)

    @property
    def extra_state_attributes(self) -> dict:
        attr = super().extra_state_attributes
        data = self.getData()

        # Add helpers for DaemonSet.
        attr["namespace"] = data.metadata.namespace

        attr["current_pods_scheduled"] = data.status.current_number_scheduled
        attr["desired_pods_scheduled"] = data.status.desired_number_scheduled
        attr["pods_available"] = data.status.number_available
        attr["pods_unavailable"] = data.status.number_unavailable

        attr["ok"] = self.is_ok()

        return attr

    @property
    def icon(self):
        if self.is_ok:
            return ICON_DAEMONSET_OK
        else:
            return ICON_DAEMONSET_NOTOK

