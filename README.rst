GleSYS DNS Authenticator for Certbot
====================================
This allows automatic completion of `Certbot's <https://github.com/certbot/certbot>`_
DNS01 challange for domains managed on `GleSYS <https://www.glesys.com/>`_ DNS.


Installing
----------
Installation of Certbot plugins are a bit tricky. The least bad way is to create
a Python virtual environment as *root* and install it there.

.. code-block::

   $ cd /root/
   $ python3 -m venv --prompt=certbot certbot
   $ source certbot/bin/activate
   $ pip install --upgrade pip setuptools
   $ pip install certbot-glesys

You can now run Certbot using ``/root/certbot/bin/certbot``.

If you use Fedora like me I have prepared
`an RPM <https://github.com/runfalk/certbot-glesys/releases>`_ you can use
instead.

.. code-block::

   $ sudo rpm -i https://github.com/runfalk/certbot-glesys/releases/download/1.0.0/python3-certbot-dns-glesys-1.0.0-1.fedora31.noarch.rpm

If you use another RPM based distribution you may be able to build it yourself.

.. code-block::

   $ source /etc/os-release
   $ python setup.py bdist_rpm --release="1.${ID}${VERSION_ID}"

PRs are welcome for other distributions.


Usage
-----
Create an API key with the following permissions:

- ``domain:list``
- ``domain:listrecords``
- ``domain:addrecord``
- ``domain:deleterecord``

Don't forget to give access to the appropriate IP-address range. If you want
to be able to run the client from anywhere, enter ``0.0.0.0/0``.

To use the authenticator you need to provide some required options:

``--certbot-glesys:auth-credentials`` *(required)*
  INI file with ``user`` and ``password`` for your GlesSYS API user.

The credentials file must have the following format:

.. code-block::

   certbot_glesys:auth_user = CL00000
   certbot_glesys:auth_password = apikeygoeshere

For safety reasons the file must not be world readable. You can solve this by
running:

.. code-block::

   $ chmod 600 credentials.ini

Then you can run ``certbot`` using:

.. code-block::

   $ certbot certonly \
       --authenticator certbot-glesys:auth \
       --certbot-glesys:auth-credentials credentials.ini \
       -d domain.com

If you want to obtain a wildcard certificate you can use the
``--server https://acme-v02.api.letsencrypt.org/directory`` flag and the domain
``-d *.domain.com``.


Disclaimer
----------
This plugin is neither affiliated with nor endorsed by GleSYS Internet Services
AB.


Changelog
=========

Version 1.0.0
-------------
Released 11th April 2020

- Changed to GleSYS JSON API
- Added RPM as an installation option
- Dropped support for EOL Python versions


Version 0.2.0
-------------
Released on 23rd April 2018

**This is a breaking change since it requires the** ``domain:list``
**permission.**

- Added proper support for sub domain guessing, pull request
  `#4 <https://github.com/runfalk/certbot-glesys/pull/4>`_
  (`@Lillecarl <https://github.com/Lillecarl>`_)


Version 0.1.1
-------------
Released on 15th March, 2018

- Bumped default propagation time to 90 seconds to improve reliability
- Fixed wrong base url in ``GlesysDomainApiClient``, pull request
  `#2 <https://github.com/runfalk/certbot-glesys/pull/2>`_
  (`@montaniasystemab <https://github.com/montaniasystemab>`_)


Version 0.1.0
-------------
Released on 30th September, 2017

- Initial release
