import logging
import itertools
import re
import zope.interface

from certbot.plugins.dns_common import DNSAuthenticator
from certbot.interfaces import IAuthenticator, IPluginFactory
from collections import namedtuple
from lxml import etree
from requests import Session
from requests.auth import HTTPBasicAuth


logger = logging.getLogger(__name__)


class DomainParts(namedtuple("DomainParts", ["domain", "subdomain"])):
    def __new__(cls, domain, subdomain=None):
        return super(DomainParts, cls).__new__(cls, domain, subdomain)

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


GlesysRecord = namedtuple("GlesysRecord", [
    "id",
    "domain",
    "subdomain",
    "type",
    "data",
    "ttl",
])


class GlesysDomainApiClient(object):
    base_url = u"https://api.glesys.com/"

    def __init__(self, username, password):
        self._client = Session()
        self._client.auth = HTTPBasicAuth(username, password)

    def _request(self, type, action, data=None):
        url = u"{}/{}/{}/".format(self.base_url, type, action)
        request = self._client.post(url, data=data)

        xml = etree.fromstring(request.content)
        status = {
            node.tag: node.text
            for node in xml.xpath("/response/status")[0]
        }

        if status["code"] != "200":
            msg = "GleSys API error: {} {}"
            raise RuntimeError(msg.format(status["code"], status["text"]))

        return xml

    def list_records(self, domain):
        xml = self._request("domain", "listrecords", {
            "domainname": domain,
        })

        for item in xml.xpath("/response/records/item"):
            attrs = {node.tag: node.text for node in item}
            yield GlesysRecord(
                id=int(attrs["recordid"]),
                domain=attrs["domainname"],
                subdomain=attrs["host"],
                type=attrs["type"],
                data=attrs["data"],
                ttl=attrs["ttl"],
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
        xml = self._request("domain", "list")
        for item in xml.xpath("/response/domains/item/domainname"):
            yield item.text

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


@zope.interface.implementer(IAuthenticator)
@zope.interface.provider(IPluginFactory)
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
        super(GlesysAuthenticator, self).__init__(*args, **kwargs)
        self._client = None
        self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add, default_propagation_seconds=90):
        super(GlesysAuthenticator, cls).add_parser_arguments(add, default_propagation_seconds)
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
