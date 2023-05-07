#!/usr/bin/env python3

import sys
import argparse
import os
import shutil
from codemeta.codemeta import load
from rdflib import Graph, URIRef, BNode
from rdflib.namespace import RDF
from codemeta.common import CODEMETA, AttribDict, getstream, SDO 
from codemeta2html.html import serialize_to_html


"""This library and command-line-tool visualises software metadata using codemeta as html."""

def main():
    """Main entrypoint for command-line usage"""
    rootpath = sys.modules['codemeta2html'].__path__[0]

    parser = argparse.ArgumentParser(description="Convert codemeta to HTML for visualisation")
    parser.add_argument('-b', '--baseuri',type=str,help="Base URI for resulting SoftwareSourceCode instances (make sure to add a trailing slash)", action='store',required=False)
    parser.add_argument('-B', '--baseurl',type=str,help="Base URL in HTML visualizations (make sure to add a trailing slash)", action='store',required=False)
    parser.add_argument('--intro', type=str, help="Set extra text (HTML) to add to the index page as an introduction", action='store',required=False)
    parser.add_argument('--css',type=str, help="Associate a CSS stylesheet (URL) with the HTML output, multiple stylesheets can be separated by a comma. This will override the internal stylesheet (add style/codemeta.css and style/fontawesome.css if you want to use it still)", action='store',  required=False)
    parser.add_argument('--no-cache',dest="no_cache", help="Do not cache context files, force redownload", action='store_true',  required=False)
    parser.add_argument('--title', type=str, help="Title to add when generating HTML pages", action='store')
    parser.add_argument('--identifier-from-file', dest='identifier_from_file', help="Derive the identifier from the filename/module name passed to codemetapy, not from the metadata itself", action='store_true',required=False)
    parser.add_argument('--outputdir', type=str,help="Output directory where HTML files are written", action='store',required=False, default="build")
    parser.add_argument('--stdout', help="Output HTML for a single resource to stdout, do not write to outputdir", action='store_true',required=False)
    parser.add_argument('--no-assets',dest="no_assets", help="Do not copy static assets (CSS, fonts) to the output directory", action='store_true',  required=False)
    parser.add_argument('files', nargs='*', help='Codemeta.json files to load (or use - for standard input). The files either contain a single software project, or are graph of multiple sofware projects')

    args = parser.parse_args()
    if args.css:
        args.css = [ x.strip() for x in args.css.split(",") ]
    else:
        args.css = ["style/codemeta.css","style/fontawesome.css"]

    if args.baseuri and not args.baseurl:
        args.baseurl = args.baseuri

    g, res, args, contextgraph = load(*args.files, **args.__dict__, buildsite=not args.stdout)
    assert isinstance(args.outputdir,str)
    if args.outputdir == ".":
        raise ValueError("Output dir may not be equal to current working directory, specify a subdirectory instead")
    if not isinstance(contextgraph, Graph):
        raise Exception("No contextgraph provided, required for HTML serialisation")

    resources = list(g.triples((None, RDF.type, SDO.SoftwareSourceCode)))
    if not resources:
        raise Exception("No resources found in JSON-LD graph")
    elif len(resources) == 1:
        doc = serialize_to_html(g, res, args, contextgraph, None)
        if args.stdout:
            print(doc)
            exit(0)

        os.makedirs(args.outputdir, exist_ok=True)
        with open(os.path.join(args.outputdir,"index.html"),'w',encoding='utf-8') as fp:
            fp.write(doc)
    else:
        print(f"Writing indices", file=sys.stderr)
        os.makedirs(args.outputdir, exist_ok=True)
        doc = serialize_to_html(g, res, args, contextgraph, None, indextemplate="cardindex.html")
        with open(os.path.join(args.outputdir, "index.html"),'w',encoding='utf-8') as fp:
            fp.write(doc)
        doc = serialize_to_html(g, res, args, contextgraph, None, indextemplate="index.html")
        os.makedirs(os.path.join(args.outputdir, "table"), exist_ok=True)
        with open(os.path.join(args.outputdir, "table", "index.html"),'w',encoding='utf-8') as fp:
            fp.write(doc)
        for res,_,_ in resources:
            assert isinstance(res, URIRef)
            print(f"Writing resource {res}", file=sys.stderr)
            if (res,SDO.identifier,None) in g:
                identifier = g.value(res, SDO.identifier)
            else:
                raise Exception(f"Resource {res} has no schema:identifier")
            resdir = os.path.join(args.outputdir,str(identifier))
            os.makedirs(resdir, exist_ok=True)
            doc = serialize_to_html(g, res, args, contextgraph, None)
            with open(os.path.join(resdir, "index.html"),'w',encoding='utf-8') as fp:
                fp.write(doc)

    if not args.no_assets:
        print(f"Copying styles", file=sys.stderr)
        stylesrcdir = os.path.join(rootpath, "style")
        styletgtdir = os.path.join(args.outputdir, "style")
        shutil.copytree(stylesrcdir, styletgtdir, dirs_exist_ok=True)


