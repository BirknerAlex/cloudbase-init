# Copyright 2020 Alexander Birkner
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import time

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.metadata.services import base
from cloudbaseinit.models import network as network_model
from cloudbaseinit.utils import encoding
from cloudbaseinit.utils import network as network_utils
from oslo_log import log as oslo_logging
from requests import RequestException

CONF = cloudbaseinit_conf.CONF
LOG = oslo_logging.getLogger(__name__)


class GPortalService(base.BaseHTTPMetadataService):
    """Metadata Service for GPortal."""
    def __init__(self):
        super(GPortalService, self).__init__(
            base_url=CONF.gportal.metadata_base_url)

        self._enable_retry = True

    def load(self):
        """Load all the available information from the metadata service."""
        super(GPortalService, self).load()

        if not CONF.gportal.metadata_base_url:
            LOG.debug('GPortal metadata url not set')
            return False

        try:
            # Try to fetch the metadata from service
            self._get_meta_data()
            return True
        except Exception as ex:
            LOG.exception(ex)
            LOG.debug('Metadata not found at URL \'%s\'' %
                      CONF.gportal.metadata_base_url)
        return False

    def get_instance_id(self):
        """Get the identifier for the current installation.

        :return str
        """
        return self._get_meta_data().get("id")

    def get_admin_password(self):
        """Get the admin password from the metadata service.

        Note:
            The password is deleted from the Backend after the first
            call of this method.

        :return str
        """
        password = None
        for _ in range(CONF.retry_count):
            try:
                metadata_url = "%s/password" % CONF.gportal.metadata_base_url
                password = encoding.get_as_string(
                    self._get_data(metadata_url)
                ).strip()
            except RequestException as ex:
                LOG.debug("Requesting the password failed: %s",
                          ex.response.status_code)
                time.sleep(CONF.retry_count_interval)
            except Exception as ex:
                LOG.exception(ex)
                time.sleep(CONF.retry_count_interval)
                continue

            if not password:
                LOG.warning("There is no password available.")
                continue

            LOG.info("The password server returned a valid password.")
            break

        return password

    def get_host_name(self):
        """Get the hostname for the server.

        :return str
        """
        return self._get_meta_data().get("fqdn")

    def get_user_data(self):
        """Get the available user data for the current instance.

        :return bytes|None
        """
        data = self._get_meta_data().get("user_data")

        if data:
            return data.encode()

    @property
    def can_post_password(self):
        """The GPortal metadata service does not support posting a password.

        :return bool
        """
        return False

    def get_network_details_v2(self):
        """Returns the network configuration in v2 format.

        :return network_model.NetworkDetailsV2
        """
        interfaces_config = self._get_meta_data().get("interfaces")
        if not interfaces_config:
            return

        links = self._net_parse_links()
        if len(links) == 0:
            LOG.warning("No network links found from metadata service")
            return

        return network_model.NetworkDetailsV2(
            links=links,
            networks=self._net_parse_subnets(),
            services=self._net_parse_services(),
        )

    def get_public_keys(self):
        """Returns public keys from meta data API

        :return []str
        """
        return self._get_meta_data().get("public_keys", [])

    def _net_parse_links(self):
        """Parses the network links from meta data

        :return []network_model.Link
        """
        links = []

        interfaces_config = self._get_meta_data().get("interfaces")
        if not interfaces_config:
            return links

        i = 0
        for t in interfaces_config:
            i += 1
            nic = interfaces_config[t][0]

            link = network_model.Link(
                id='interface%s' % i,
                name="Network %s" % t,
                type=network_model.LINK_TYPE_PHYSICAL,
                enabled=True,
                mac_address=nic.get("mac").upper(),
                mtu=nic.get("mtu", 1500),
                bond=None,
                vlan_link=None,
                vlan_id=None,
            )
            links.append(link)

        return links

    def _net_parse_subnets(self):
        """Parses the networks from meta data

        :return []network_model.Network
        """
        networks = []

        interfaces_config = self._get_meta_data().get("interfaces")
        if not interfaces_config:
            return networks

        dns_config = self._get_meta_data().get("dns")
        if not dns_config:
            return networks

        additional_routes = self._get_meta_data().get("routes", [])

        i = 0
        for nic_type in interfaces_config:
            i += 1
            nic = interfaces_config[nic_type][0]

            for ip_version in ['ipv4', 'ipv6']:
                subnet = nic.get(ip_version, None)
                if not subnet:
                    continue

                if ip_version == 'ipv4':
                    default_gateway_cidr = "0.0.0.0/0"
                else:
                    default_gateway_cidr = "::/0"

                routes = []
                nameservers = []
                # Only the public interface has a gateway address
                # and nameservers
                if nic_type == "public":
                    routes.append(network_model.Route(
                        network_cidr=default_gateway_cidr,
                        gateway=subnet.get('gateway')
                    ))

                    nameservers = dns_config.get("nameservers", [])

                for r in additional_routes:
                    routes.append(network_model.Route(
                        network_cidr=r.get('destination'),
                        gateway=r.get('gateway')
                    ))

                networks.append(network_model.Network(
                    link="Network %s" % nic_type,
                    address_cidr=network_utils.ip_netmask_to_cidr(
                        subnet.get('address'), subnet.get('netmask')
                    ),
                    routes=routes,
                    dns_nameservers=nameservers,
                ))

        return networks

    def _net_parse_services(self):
        """Parses the network services from meta data

        :return []network_model.NameServerService
        """
        services = []

        dns_config = self._get_meta_data().get("dns")
        if not dns_config:
            return services

        services.append(network_model.NameServerService(
            addresses=dns_config.get("nameservers", []),
            search=None
        ))

        return services

    def _get_meta_data(self):
        """Returns the full metadata object from the metadata service.

        :return object
        """
        data = self._get_cache_data(
            "%s/v1.json" % CONF.gportal.metadata_base_url,
            decode=True
        )
        if data:
            return json.loads(data)
