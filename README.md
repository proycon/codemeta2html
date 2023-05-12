[![Project Status: Active -- The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![GitHub release](https://img.shields.io/github/release/proycon/codemeta2html.svg)](https://GitHub.com/proycon/codemeta2html/releases/)
[![Latest release in the Python Package Index](https://img.shields.io/pypi/v/codemeta2html)](https://pypi.org/project/codemeta2html/)
 
# Codemeta2html

## Introduction

Codemeta2html is a command-line tool and software library to visualize software
metadata in the [codemeta](https://codemeta.github.io) standard. This library
builds on [codemetapy](https://github.com/proycon/codemetapy).

### Features

* Generates a complete static website with:
    * rich [RDFa](https://www.w3.org/TR/rdfa-primer/) data (codemeta/schema.org/etc) embedded in the HTML,
      expressing as much of the input linked data as possible. This means though we visualise for humans, we do 
      not sacrifice on machine parsability and semantic interpretability.
    * index pages (card view & table view)
    * one dedicated page per software source project
    * client-side filtering (faceted search) capabilities
    * direct access to the underlying JSON-LD and Turtle serialisations per source project and for the complete data graph as a whole
    * responsive layout suitable for different devices and screen-sizes
    * minimal amount of external web calls (only for github/gitlab badges and for external resources references directly by the software metadata itself)
    * minimal client-side javascript, also usable without (except for filtering)
    * useful in combination with [codemeta-harvester](https://github.com/proycon/codemeta-harvester) to visualize the results of the harvest

### Notes

1. This solution is designed to work well with tens or hundreds of
resources (software projects), it does not scale well beyond that to thousands
of resources.
2. If you want a server-side solution that allows for live querying (using SPARQL),
then use [codemeta-server](https://github.com/proycon/codemeta-server) instead
(which has this project as main dependency).

## Installation

`pip install codemeta2html`

## Usage

You can pass either a JSON-LD file describing a single software project and
have it output to standard output:

`$ codemeta2html --stdout yoursoftware.codemeta.json > yoursoftware.html`

Or you can pass a full JSON-LD graph describing multiple projects, effectively
using `codemeta2html` to generate a static website:

`$ codemeta2html --outputdir build/ yoursoftware.codemeta.json`

This is the default behaviour, it also works on an input file for  single
software project although it may be overkill there.


You can pass additional linked data (JSON-LD or turtle) to the context graph, this is used for
vocabularies that are referenced by the software metadata and ensures they can
be properly labelled in the visualisation. The use of SKOS vocabularies is supported and encouraged.
Consider the following example for the CLARIAH project:

`
$ codemeta2html --title "CLARIAH Tools" --baseuri https://tools.clariah.nl/ --addcontextgraph https://w3id.org/nwo-research-fields --addcontextgraph https://raw.githubusercontent.com/CLARIAH/tool-discovery/master/schemas/research-technology-readiness-levels.jsonld --addcontextgraph https://vocabs.dariah.eu/rest/v1/tadirah/data\?format\=text/turtle data.json
`

The `--baseuri` parameter will adapt all resource identifiers to a single
common URI, which does not necessarily have to be the same as the URL the pages
are served from (you can use ``--baseurl`` for that).


## Acknowledgement

This work is conducted at the [KNAW Humanities Cluster](https://huc.knaw.nl/)'s
[Digital Infrastructure department](https://di.huc.knaw.nl/) in the scope of the 
[CLARIAH](https://www.clariah.nl) project (CLARIAH-PLUS, NWO grant 184.034.023) as
part of the FAIR Tool Discovery track of the Shared Development Roadmap.
