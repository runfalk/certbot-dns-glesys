import pytest
from certbot_dns_glesys import DomainParts, GlesysAuthenticator, GlesysRecord
from unittest.mock import MagicMock


# This config just sets all parameters to some value. It's just to make sure
# that the DNSAuthenticator constructor has all the parameters it might need
class PluginConfig:
    verb = "certonly"
    config_dir = "/tmp/cfg"
    work_dir = "/tmp/work"
    logs_dir = "tmp/log"
    cert_path = "./cert.pem"
    fullchain_path = "./chain.pem"
    chain_path = "./chain.pem"
    server = "https://acme-v02.api.letsencrypt.org/directory"


class GlesysTestAuthenticator(GlesysAuthenticator):
    def __init__(self, client):
        super().__init__(config=PluginConfig, name="dns-glesys")
        self._test_client = client
    def _get_glesys_client(self):
        return self._test_client


@pytest.mark.parametrize("full_domain", [
    "runfalk.se",
    "*.runfalk.se",
    "acme-v02.api.letsencrypt.org",
])
def test_domain_parts_init(full_domain):
    d = DomainParts(full_domain)
    assert d.domain == full_domain
    assert d.subdomain is None


def test_domain_parts_iter_variants():
    d = DomainParts("*.runfalk.se")
    expected_variants = {
        d,
        DomainParts("runfalk.se", "*"),
        DomainParts("se", "*.runfalk"),
    }
    assert set(d.iter_variants()) == expected_variants


def test_domain_parts_iter_variants_complex():
    d = DomainParts("acme-v02.api.letsencrypt.org")
    expected_variants = {
        d,
        DomainParts("api.letsencrypt.org", "acme-v02"),
        DomainParts("letsencrypt.org", "acme-v02.api"),
        DomainParts("org", "acme-v02.api.letsencrypt"),
    }
    assert set(d.iter_variants()) == expected_variants


def test_perform_cleanup_cycle():
    domain = "*.runfalk.se"  # Unused
    validation_domain = "_acme-challenge.runfalk.se"
    validation_key = "thisgoesinthetetxtrecord"

    glesys_mock = MagicMock()
    def split_domain(d):
        assert d == validation_domain
        return DomainParts("runfalk.se", "_acme-challenge")
    glesys_mock.split_domain.side_effect = split_domain

    auth = GlesysTestAuthenticator(glesys_mock)
    auth._perform(domain, validation_domain, validation_key)
    glesys_mock.add_record.assert_called_with(
        domain="runfalk.se",
        subdomain="_acme-challenge",
        type="TXT",
        data=validation_key,
        ttl=auth.ttl,
    )

    record_id = 20200411
    glesys_mock.list_records.return_value = [
        GlesysRecord(record_id, "runfalk.se", "_acme-challenge", "TXT", validation_key, auth.ttl),
    ]
    auth._cleanup(domain, validation_domain, validation_key)
    glesys_mock.remove_record.assert_called_with(record_id)
