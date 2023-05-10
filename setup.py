#!/usr/bin/env python3

import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname),'r',encoding='utf-8').read()

setup(
    name = "codemeta2html",
    version = "0.1.0", #also adapt in codemeta.json
    author = "Maarten van Gompel",
    author_email = "proycon@anaproy.nl",
    description = "Convert software metadata in codemeta to html for visualisation",
    license = "GPL-3.0-only",
    keywords = [ "software metadata", "codemeta", "schema.org", "rdf", "linked data"],
    url = "https://github.com/proycon/codemeta2html",
    packages=['codemeta2html'],
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Software Development",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    zip_safe=False,
    include_package_data=True,
    package_data = { 'codemeta2html': ['templates/*.html','style/*.css', 'style/fa-*', 'style/*.js' ] },
    install_requires=[ 'codemetapy','Jinja2 >= 2.9', 'rdflib'],
    entry_points = {    'console_scripts': [ 'codemeta2html = codemeta2html.codemeta2html:main' ] },
)
