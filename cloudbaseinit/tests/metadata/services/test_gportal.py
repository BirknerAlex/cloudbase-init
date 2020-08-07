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

import importlib
import unittest

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.models import network as nm

try:
    import unittest.mock as mock
except ImportError:
    import mock

import json

CONF = cloudbaseinit_conf.CONF
MODULE_PATH = "cloudbaseinit.metadata.services.gportal"

ADMIN_PASSWORD = b"MySecretAdministratorPassword123!"

# Copies from a running server
METADATA = json.loads("""
{
  "id": "3f657fa2-7b72-466e-bad4-f83a31fbe5cd",
  "type": "BARE_METAL",  
  "fqdn": "server1",
  "region": "FRA01",
  "public_keys": [
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCdggAqqRKDj8X9ckZzJ0tB/r/VF6pD5JqP6c2/BHL9ctSae5TQClyOpSJdbp395MCjF3xOe89uK2MeOzUsYNMsTrwYPpFfpndnyAmY8Dc8L/iniqtFnHBCFS+z5VAx1mZNHdRS3NEhTkzPrt7PdmcJ1+cyfrUo9+w3kJMLuc3iyj5ZsoAp7anGtQKLCCxIL5fFCAQcYZR8w/AvLIj4B8sCb6Mon4TF9QhAJB1KbUhEwe3PY3tP1IkjYve9mKM6D5JF/b27ylRvliLLiq92LD/tBjJWjAaw92BqC3fa+Yfx9O+bCrNyP2yFX15L3/nbkppxmlZkk7aHuovkc3W6I5FlcbQfXMUjmMafdA/5Kmss5mgoq0q0E5nWhUu4L2NMW5VAkeTv+lsWLhj1vCo9JC3408mgiNaUn0XNq+uC4J6nXF/qYFNq5XvJPDsaxcxDBJip9dl9a/5BGbo6gAfORMJ1NTzpumKlEIoWZjk/TYVP7Za81UppUkk/n5x8spN70ZxoSIjQ8mXsY/GJ0uAycmy8UYH2hnDmNXiFFEh2E3iDwHYxUaoCVy/kwKBZc7kf1Rc3Fnf+Bt0PU2+k3msqBbpej3ZIoHGMdAaHpI6yYj6c60HC6PYClskkFufbGqyAtN6DcnDD3BthHS096BaTvwpIRRpyrYcPBs4gAccDbX//qw==",
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDEWZnqgDcJhyK1x7m5X6FNDIeBqM/ekFQbBUreIUW8b2pOhG1ldymCBXWONfhauuNonf9+tz1pEYNzSN7JBpHZYEraETjs32mV+X8ufHdLJhTxUM6KTjfFRRihYEHlD60URZtPFKxQStyue7s9YK02nVTALll1TyuV4wKfkP51V3AFMFjxw00i2swT19RhRTYNYzl8i7E8K14oMDEMFYlmLMeuOMpqJoORvZUX+lBKqn9eLsQmah4LssdVzP0bxMZXCGh+4j9XCk2eroyCgh7lO+obQlZxjltUIXLU/+UtOJIItpI3/2Ux/G8NCZ/FoZllIZwWuEJtB95mSX0g1uLDqSmgTbmvO56njQ8oC/KZMlX1IEEM56uUzPeLpQkclw6EEDsXLGhYn8S44u4PSYdC7DhprbRwNVbfgzfbpfnSSrqbnf1Z0ZugYT+0i8zx5ZyTHDiuN7dvvE8zVW/Oza+DZCctPsFW5RZIQiUENcJdf/NioCCgzJO8slh1RKc8lHpkxyN6YlbY6TbNv9x9Fpi5tHUI1vSeIQ75wTBrTIecIjNJNWZAkqQn2TVwdL6r2FG6Q/Avz2brCybUcNb0Pem3kn9BWrACbN1KPPRb9/iY+3wun8Bzq7CV9/JDrtgzCwFXM44fFiUnzYQgfvG9VpLvq8IVpIFhNlQAvkkNaLZuww=="
  ],
  "interfaces": {
    "public": [
      {
        "ipv4": {
          "address": "176.57.186.5",
          "netmask": "255.255.255.0",
          "gateway": "176.57.186.1"
        },
        "mac": "40:9a:4c:8d:96:77",
        "type": "public"
      }
    ]
  },
  "dns": {
    "nameservers": [
      "8.8.8.8",
      "1.1.1.1"
    ]
  },
  "routes": [
    {
      "destination": "169.254.169.254/32",
      "gateway": "176.57.186.1",
      "metric": 1000
    }
  ]
}
""")  # noqa: W291, E501


class GPortalServiceTest(unittest.TestCase):
    """Tests the GPortal metadata service"""
    def setUp(self):
        module = importlib.import_module(MODULE_PATH)
        self._service = module.GPortalService()

    @mock.patch('%s.GPortalService._get_cache_data' % MODULE_PATH)
    def _test_get_metadata(self, mock_get_cache_data):
        mock_get_cache_data.return_value = json.dumps(METADATA)

        response = self._service._get_meta_data()
        mock_get_cache_data.assert_called_with(
            '%s/v1.json' % CONF.gportal.metadata_base_url,
            decode=True)

        self.assertEqual(response, METADATA)

    @mock.patch('%s.GPortalService._get_data' % MODULE_PATH)
    def test_get_admin_password(self, mock_get_data):
        mock_get_data.return_value = ADMIN_PASSWORD

        response = self._service.get_admin_password()
        mock_get_data.assert_called_with(
            '%s/password' % CONF.gportal.metadata_base_url)

        self.assertEqual(response, str(ADMIN_PASSWORD, 'utf-8'))

    @mock.patch('%s.GPortalService._get_meta_data' % MODULE_PATH)
    def test_get_instance_id(self, mock_get_meta_data):
        mock_get_meta_data.return_value = METADATA

        response = self._service.get_instance_id()
        mock_get_meta_data.assert_called_once_with()

        self.assertEqual(METADATA.get('id'), response)

    @mock.patch('%s.GPortalService._get_meta_data' % MODULE_PATH)
    def test_get_hostname(self, mock_get_meta_data):
        mock_get_meta_data.return_value = METADATA

        response = self._service.get_host_name()
        mock_get_meta_data.assert_called_once_with()

        self.assertEqual(METADATA.get('fqdn'), response)

    @mock.patch('%s.GPortalService._get_meta_data' % MODULE_PATH)
    def test_empty_get_user_data(self, mock_get_meta_data):
        mock_get_meta_data.return_value = METADATA

        response = self._service.get_user_data()
        mock_get_meta_data.assert_called_once_with()

        self.assertIsNone(response)

    @mock.patch('%s.GPortalService._get_meta_data' % MODULE_PATH)
    def test_existing_get_user_data(self, mock_get_meta_data):
        METADATA['user_data'] = "#ps1\nNew-Item C:/test.txt"
        mock_get_meta_data.return_value = METADATA

        response = self._service.get_user_data()
        mock_get_meta_data.assert_called_once_with()

        real_metadata = METADATA.get('user_data')
        if real_metadata:
            real_metadata = real_metadata.encode()

        self.assertIsInstance(response, bytes)
        self.assertEqual(real_metadata, response)

    @mock.patch('%s.GPortalService._get_meta_data' % MODULE_PATH)
    def test_get_public_keys(self, mock_get_meta_data):
        mock_get_meta_data.return_value = METADATA

        response = self._service.get_public_keys()
        mock_get_meta_data.assert_called_once_with()

        self.assertEqual(len(response), 2)
        self.assertEqual(METADATA.get('public_keys'), response)

    def test_can_post_password(self):
        self.assertEqual(self._service.can_post_password, False)

    @mock.patch('%s.GPortalService._get_meta_data' % MODULE_PATH)
    def test_network_details_v2(self, mock_get_meta_data):
        mock_get_meta_data.return_value = METADATA

        response = self._service.get_network_details_v2()
        mock_get_meta_data.assert_called()

        links = [nm.Link(
            id='interface1',
            name='Network public',
            type=nm.LINK_TYPE_PHYSICAL,
            enabled=True,
            mac_address="40:9A:4C:8D:96:77",
            mtu=1500,
            bond=None,
            vlan_link=None,
            vlan_id=None,
        )]

        networks = [nm.Network(
            link='Network public',
            address_cidr='176.57.186.5/24',
            dns_nameservers=['8.8.8.8', '1.1.1.1'],
            routes=[
                nm.Route(network_cidr='0.0.0.0/0',
                         gateway="176.57.186.1"),
                nm.Route(network_cidr='169.254.169.254/32',
                         gateway="176.57.186.1"),
            ]
        )]

        services = [nm.NameServerService(
            addresses=['8.8.8.8', '1.1.1.1'],
            search=None)]

        self.assertEqual(response.links, links)
        self.assertEqual(response.networks, networks)
        self.assertEqual(response.services, services)
