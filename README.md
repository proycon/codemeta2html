[![Project Status: Active -- The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![GitHub release](https://img.shields.io/github/release/proycon/codemeta2html.svg)](https://GitHub.com/proycon/codemeta2html/releases/)
[![Latest release in the Python Package Index](https://img.shields.io/pypi/v/codemeta2html)](https://pypi.org/project/codemeta2html/)
 
# Codemeta2html

Codemeta2html is a command-line tool and software library to visualize software metadata in the [codemeta](https://codemeta.github.io) standard.
This library build on [codemetapy](https://github.com/proycon/codemetapy).

## Installation

`pip install codemeta2html`

## Usage

You can pass either a JSON-LD file describing a single software project:

`$ codemeta2html yoursoftware.codemeta.json > yoursoftware.html`

You can pass a full JSON-LD graph describing multiple projects, effectively using `codemeta2html` to generate a static website:

`$ codemeta2html --outputdir build/ yoursoftware.codemeta.json`

