#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Charm the service.

Refer to the following post for a quick-start guide that will help you
develop a new k8s charm using the Operator Framework:

    https://discourse.charmhub.io/t/4208
"""

import logging

from charms.loki_k8s.v0.loki import LokiProvider
from loki_server import LokiServer
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus

logger = logging.getLogger(__name__)

PORT = 3100

class LokiOperatorCharm(CharmBase):
    """Charm the service."""

    _stored = StoredState()
    loki_provider: LokiProvider = None

    def __init__(self, *args):
        super().__init__(*args)
        self._stored.set_default(provider_ready=False)
        self.framework.observe(self.on.loki_pebble_ready, self._on_loki_pebble_ready)

    ##############################################
    #           CHARM HOOKS HANDLERS             #
    ##############################################
    def _on_loki_pebble_ready(self, event):
        """Define and start a workload using the Pebble API."""
        # Get a reference the container attribute on the PebbleReadyEvent
        container = event.workload
        # Define an initial Pebble layer configuration
        target = self.config["target"]
        pebble_layer = {
            "summary": "Loki layer",
            "description": "pebble config layer for Loki",
            "services": {
                "loki": {
                    "override": "replace",
                    "summary": "loki",
                    "command": f"/usr/bin/loki -target={target} -config.file=/etc/loki/local-config.yaml",
                    "startup": "enabled",
                },
            },
        }
        # Add intial Pebble config layer using the Pebble API
        container.add_layer("loki", pebble_layer, combine=True)
        # Autostart any services that were defined with startup: enabled
        container.autostart()
        self._provide_loki()

    ##############################################
    #             UTILITY METHODS                #
    ##############################################
    def _provide_loki(self):
        if self.provider_ready:
            self.loki_provider = LokiProvider(self, "loki", "loki", LokiServer().version)
            self.loki_provider.ready()
            logger.debug("Loki Provider is available")
            self.unit.status = ActiveStatus()

    ##############################################
    #               PROPERTIES                   #
    ##############################################
    @property
    def provider_ready(self):
        """Check status of Loki server.

        Status of the Loki services is checked by querying
        Loki for its version information. If Loki responds
        with valid information, its status is recorded.

        Returns:
            True if Loki is ready, False otherwise
        """
        provided = {"loki": LokiServer().version}

        if provided["loki"] is not None:
            logger.debug("Loki provider is available")
            logger.debug("Providing : %s", provided)
            self._stored.provider_ready = True

        return self._stored.provider_ready

    @property
    def unit_ip(self) -> str:
        """Returns unit's IP"""
        if bind_address := self.model.get_binding("loki").network.bind_address:
            return str(bind_address)
        return ""


if __name__ == "__main__":
    main(LokiOperatorCharm)
