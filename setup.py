#!/usr/bin/env python
"""Navigator
    Web Framework based on aiohttp, with batteries included.
See:
https://bitbucket.org/mobileinsight1/navigator/src/master/
"""

from setuptools import setup, find_packages

setup(
    name='navigator',
    version=open("VERSION").read().strip(),
    python_requires=">=3.8.0",
    url='https://bitbucket.org/mobileinsight1/navigator/',
    download_url="https://bitbucket.org/mobileinsight1/navigator/",
    description='Asyncio Web Framework',
    keywords=["asyncio", "REST", "Framework", "datasources", 'protocol', 'aiohttp', 'web'],
    long_description=open("README.md").read(),
    license="BSD",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'License :: OSI Approved :: BSD License',
    ],
    author='Jesus Lara',
    author_email='jlara@trocglobal.com',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=[
        'numpy >= 1.11.1',
        'asyncio==3.4.3',
        'aiohttp>=3.0.0,<4.0.0',
        'setuptools',
        'sockjs==0.10.0',
        'python-dotenv==0.14.0',
        'pydantic==1.6.1',
        'cchardet==2.1.6',
        'aiodns==2.0.0',
        'brotlipy==0.7.0',
        'pycares==3.1.1',
        'aiofile==3.0.0',
        'pylibmc==1.6.1',
        'aiojobs==0.2.2',
        'aiohttp-session',
        'aiohttp-jrpc',
        'cryptography',
        'aiohttp-cors==0.7.0',
        'uvloop==0.14.0',
        'objectpath==0.6.1',
        'aiohttp-debugtoolbar==0.6.0',
        'aiohttp-jinja2==1.2.0',
        'aiohttp-session==2.9.0',
        'aiohttp-swagger==1.0.15',
        'aiohttp-utils==3.1.1',
        'wheel==0.34.2',
        'aiosocks==0.2.6'
    ],
    dependency_links=[
        'git+git@bitbucket.org:mobileinsight1/asyncdb.git@a7ff6c85df0f94cbae29cc31fbab2f366fad2be7#egg=asyncdb',
    ],
    project_urls={  # Optional
        'Source': 'https://bitbucket.org/mobileinsight1/navigator/',
        'Funding': 'https://paypal.me/phenobarbital',
        'Say Thanks!': 'https://saythanks.io/to/phenobarbital',
    },
)
