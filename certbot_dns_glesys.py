import logging
import itertools
import re

from certbot.plugins.dns_common import DNSAuthenticator
from requests import Session
from requests.auth import HTTPBasicAuth
from typing import NamedTuple


logger = logging.getLogger(__name__)


class DomainParts(NamedTuple):
    domain: str
    subdomain: str = None

    def iter_variants(self):
        sub_parts = []
        if self.subdomain is not None:
            sub_parts = self.subdomain.split(".")

        parts = self.domain.split(".")
        for i in range(len(parts)):
            yield DomainParts(
                ".".join(parts[i:]),
                ".".join(sub_parts + parts[:i]) or None,
            )


class GlesysRecord(NamedTuple):
    id: int
    domain: str
    subdomain: str
    type: str
    data: str
    ttl: int


class GlesysDomainApiClient:
    base_url = u"https://api.glesys.com/"

    def __init__(self, username, password):
        self._client = Session()
        self._client.auth = HTTPBasicAuth(username, password)
        self._client.headers["Accept"] = "application/json"

    def _request(self, type, action, data=None):
        url = u"{}/{}/{}/".format(self.base_url, type, action)
        rsp = self._client.post(url, data=data).json()["response"]
        status = rsp["status"]

        if status["code"] != 200:
            raise RuntimeError("GleSys API error: {} {} (debug: {!r})".format(
                status["code"],
                status["text"],
                rsp.get("debug"),
            ))

        return rsp

    def list_records(self, domain):
        rsp = self._request("domain", "listrecords", {
            "domainname": domain,
        })

        for record in rsp["records"]:
            # ID and TTL are ints, the int() call is just there for validation
            yield GlesysRecord(
                id=int(record["recordid"]),
                domain=record["domainname"],
                subdomain=record["host"],
                type=record["type"],
                data=record["data"],
                ttl=int(record["ttl"]),
            )

    def add_record(self, domain, subdomain, type, data, ttl=None):
        args = {
            "domainname": domain,
            "host": subdomain,
            "type": type,
            "data": data,
        }

        if ttl is not None:
            args["ttl"] = ttl

        return self._request("domain", "addrecord", args)

    def remove_record(self, record_id):
        return self._request("domain", "deleterecord", {
            "recordid": record_id,
        })

    def list_domains(self):
        """Return an iterator of domain names manageable by the current user"""
        rsp = self._request("domain", "list")
        for domain in rsp["domains"]:
            yield domain["domainname"]

    def split_domain(self, domain):
        """
        Split the domain into a DomainParts object.

        The returned domain is guaranteed to exist on GleSYS. If the domain is
        not available this will raise ValueError.
        """
        domains = list(self.list_domains())
        for dp in DomainParts(domain).iter_variants():
            if dp.domain not in domains:
                continue
            return dp

        raise ValueError("Unable to find domain in GleSYS control panel")


class GlesysAuthenticator(DNSAuthenticator):
    """
    GleSYS DNS ACME authenticator.

    This Authenticator uses the Glesys API to fulfill a dns-01 challenge.
    """

    #: Short description of plugin
    description = __doc__.strip().split("\n", 1)[0]

    #: TTL for the validation TXT record
    ttl = 60

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add, default_propagation_seconds=90):
        super().add_parser_arguments(add, default_propagation_seconds)
        add("credentials", help="GleSYS API credentials INI file.")

    def more_info(self):
        """More in-depth description of the plugin."""
        return "\n".join(line[4:] for line in __doc__.strip().split("\n"))

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            "credentials",
            "Glesys credentials INI file",
            {
                "user": "API username for GleSYS account",
                "password": "API password for GleSYS account",
            },
        )

    def _get_glesys_client(self):
        return GlesysDomainApiClient(
            self.credentials.conf("user"),
            self.credentials.conf("password"),
        )

    def _perform(self, domain, validation_name, validation):
        glesys = self._get_glesys_client()

        domain_parts = glesys.split_domain(validation_name)

        msg = u"Creating TXT record for {domain} on subdomain {subdomain}"
        logger.debug(msg.format(
            domain=domain_parts.domain,
            subdomain=domain_parts.subdomain,
        ))

        glesys.add_record(
            domain=domain_parts.domain,
            subdomain=domain_parts.subdomain,
            type="TXT",
            data=validation,
            ttl=self.ttl,
        )

    def _cleanup(self, domain, validation_name, validation):
        glesys = self._get_glesys_client()

        domain_parts = glesys.split_domain(validation_name)
        msg = "Removing TXT record for domain {domain} on subdomain {subdomain}"
        logger.debug(msg.format(
            domain=domain_parts.domain,
            subdomain=domain_parts.subdomain,
        ))

        subdomain_to_id = {
            record.subdomain: record.id
            for record in glesys.list_records(domain_parts.domain)
            if record.type == "TXT" and record.data == validation
        }

        record_id = subdomain_to_id[domain_parts.subdomain]
        logger.debug("Removing record ID {}".format(record_id))
        glesys.remove_record(record_id)
