import sys
import os.path
from datetime import datetime
from rdflib import Graph, URIRef, BNode, Literal
from rdflib.namespace import RDF, SKOS, RDFS
from typing import Union, IO
from codemeta.common import AttribDict, REPOSTATUS, license_to_spdx, SDO, CODEMETA, SOFTWARETYPES, SCHEMA_SOURCE, CODEMETA_SOURCE, CONTEXT, DUMMY_NS, SCHEMA_LOCAL_SOURCE, SCHEMA_SOURCE, CODEMETA_LOCAL_SOURCE, CODEMETA_SOURCE, STYPE_SOURCE, STYPE_LOCAL_SOURCE, init_context, SINGULAR_PROPERTIES, merge_graphs
from codemeta import __path__ as rootpath
from jinja2 import Environment, FileSystemLoader

def get_triples(g: Graph, res: Union[URIRef,BNode,None], prop, labelprop=SDO.name, abcsort=False):
    results = []
    havepos = False
    for _,_, res2 in g.triples((res, prop, None)):
        if isinstance(res2, Literal):
            results.append( (res2, res2, None) )
        else:
            pos = g.value(res2, SDO.position)
            if pos is not None:
                havepos = True
            label = g.value(res2, labelprop)
            if label:
                results.append((label, res2, pos))
            else:
                results.append((res2, res2, pos))
    if havepos:
        results.sort(key=lambda x: x[2])
    if abcsort:
        results.sort()
    return [ tuple(x[:2]) for x in results ]

def get_index(g: Graph):
    results = []
    for res,_,_ in g.triples((None, RDF.type, SDO.SoftwareSourceCode)):
        label = g.value(res, SDO.name)
        results.append((res, label))
    results.sort(key=lambda x: x[1])
    return results



def parse_github_url(s):
    if not s: return None
    if s.endswith(".git"): s = s[:-4]
    if s.startswith("https://github.com/"):
        owner, repo = s.replace("https://github.com/","").split("/")
        return owner, repo
    return None, None

def get_badge(g: Graph, res: Union[URIRef,None], key):
    owner, repo = parse_github_url(g.value(res, SDO.codeRepository))
    if owner and repo:
        #github badges
        if key == "stars":
            yield f"https://img.shields.io/github/stars/{owner}/{repo}.svg?style=flat&color=5c7297", None, "Stars are an indicator of the popularity of this project on GitHub"
        elif key == "issues":
            yield f"https://img.shields.io/github/issues/{owner}/{repo}.svg?style=flat&color=5c7297", None, "The number of open issues on the issue tracker"
            yield f"https://img.shields.io/github/issues-closed/{owner}/{repo}.svg?style=flat&color=5c7297", None, "The number of closes issues on the issue tracker"

def type_label(g: Graph, res: Union[URIRef,None]):
    label = g.value(res, RDF.type)
    if label:
        label = label.split("/")[-1]
        return label
    else:
        return ""


def get_interface_types(g: Graph, res: Union[URIRef,None], contextgraph: Graph, fallback= False):
    """Returns labels and definitions (2-tuple) for the interface types that this SoftwareSourceCode resource provides"""
    types =  set()
    for _,_,res3 in g.triples((res, RDF.type, None)):
        if res3 != SDO.SoftwareSourceCode:
            stype =  contextgraph.value(res3, RDFS.label)
            comment = contextgraph.value(res3, RDFS.comment) #used for definitions
            if stype:
                types.add((stype,comment))
    for _,_,res2 in g.triples((res, SDO.targetProduct, None)):
        for _,_,res3 in g.triples((res2, RDF.type, None)):
            stype =  contextgraph.value(res3, RDFS.label)
            comment = contextgraph.value(res3, RDFS.comment) #used for definitions
            if stype:
                types.add((stype,comment))

    if not types and fallback:
        types.add(("Unknown", "Sorry, we don't know what kind of interfaces this software provides. No interface types have been specified or could be automatically extracted."))
    return list(sorted(types))



def serialize_to_html(g: Graph, res: Union[URIRef,None], args: AttribDict, contextgraph: Graph) -> dict:
    """Serialize to HTML with RDFa"""

    env = Environment( loader=FileSystemLoader(os.path.join(rootpath[0], 'templates')), autoescape=True)
    if res:
        template = env.get_template("softwaresourcecode.html")
        index = []
    else:
        template = env.get_template("index.html")
        index = get_index(g)
    return template.render(g=g, res=res, SDO=SDO,CODEMETA=CODEMETA, RDF=RDF, STYPE=SOFTWARETYPES, REPOSTATUS=REPOSTATUS, SKOS=SKOS, get_triples=get_triples, type_label=type_label, css=args.css, contextgraph=contextgraph, URIRef=URIRef, get_badge=get_badge, now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), index=index, get_interface_types=get_interface_types,baseuri=args.baseuri)



