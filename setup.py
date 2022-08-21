import os
from pathlib import Path
from distutils.command.bdist_rpm import bdist_rpm
from setuptools import setup


# We need this hack since distutils doesn't allow overriding the name of the
# package
class SpecOverrideBdistRpm(bdist_rpm):
    def _make_spec_file(self):
        # We use pkg_name since %{name} seems to be overridden with the python3-
        # prefixed one after it's been used for the "Name:" field
        spec = ["%define pkg_name certbot-dns-glesys"]
        for line in super()._make_spec_file():
            if line.startswith("Name:"):
                spec.append("Name: python3-%{pkg_name}")
            elif line.startswith("Source0:"):
                spec.append("Source0: %{pkg_name}-%{unmangled_version}.tar.gz")
            elif line.startswith("%setup"):
                spec.append("%setup -n %{pkg_name}-%{unmangled_version}")
            else:
                spec.append(line)
        return spec


try:
    long_desc = open("README.rst").read()
except:
    print("Skipping README.rst for long description as it was not found")
    long_desc = None

setup(
    name="certbot-dns-glesys",
    version="2.1.0",
    description="GleSYS DNS authentication plugin for Certbot",
    long_description=long_desc,
    license="BSD",
    author="Andreas Runfalk",
    author_email="andreas@runfalk.se",
    url="https://www.github.com/runfalk/certbot-dns-glesys",
    py_modules=["certbot_dns_glesys"],
    install_requires=[
        "acme>=1.8.0",
        "certbot>=1.7.0",
        "requests",
    ],
    extras_require={
            "dev": [
                "pytest",
                "wheel",
            ],
    },
    entry_points={
        "certbot.plugins": [
            "dns-glesys = certbot_dns_glesys:GlesysAuthenticator",
        ],
    },
    cmdclass={
        "bdist_rpm": SpecOverrideBdistRpm,
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Plugins",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Internet :: Name Service (DNS)",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
)
