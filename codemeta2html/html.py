import sys
import os.path
from datetime import datetime
from collections import OrderedDict, defaultdict
import codemeta.parsers.gitapi
import unicodedata
import re
import json
from hashlib import md5
from rdflib import Graph, URIRef, BNode, Literal
#pyri
from rdflib import RDF, SKOS, RDFS #type: ignore
from typing import Union, IO, Optional, Sequence, Iterator
from itertools import chain

if sys.version_info.minor < 8:
    from importlib_metadata import version as get_version  # backported
else:
    from importlib.metadata import version as get_version
from codemeta.common import (
    AttribDict,
    REPOSTATUS,
    SDO,
    CODEMETA,
    SOFTWARETYPES,
    SOFTWAREIODATA,
    TRL,
    CODEMETAPY,
    ORDEREDLIST_PROPERTIES,
    get_last_component,
    query,
    iter_ordered_list,
    get_doi,
)
import codemeta.parsers.gitapi
from jinja2 import Environment, FileSystemLoader


def get_triples(
    g: Graph,
    res: Union[URIRef, BNode, None],
    prop,
    labelprop=(SDO.name, SDO.legalName, RDFS.label, SKOS.prefLabel),
    abcsort=False,
    contextgraph: Optional[Graph] = None,
    max=0,
):
    """Get all triples for a particular resource and properties, also returns labels which are looked for in the contextgraph when needed, and handles sorting"""
    results = []
    havepos = False
    if not isinstance(labelprop, (tuple, list)):
        labelprop = (labelprop,)
    if res is not None and prop in ORDEREDLIST_PROPERTIES:
        triples = iter_ordered_list(g, res, prop)
    else:
        triples = g.triples((res, prop, None))
    for i, (_, _, res2) in enumerate(triples):
        if (
            isinstance(res2, Literal)
            and str(res2).startswith(("http", "_", "/"))
            and (URIRef(res2), None, None) in g
        ):
            # if a literals referers to an existing URI in the graph, treat it as a URIRef instead
            res2 = URIRef(str(res2))
        if isinstance(res2, Literal):
            results.append((res2, res2, 9999, 9999))
        else:
            if prop in ORDEREDLIST_PROPERTIES:
                # already returned in order
                pos = i
            else:
                # follow schema:position if available
                pos = g.value(res2, SDO.position)
                if pos is not None:
                    havepos = True
                elif isinstance(pos, int):
                    pass
                elif isinstance(pos, str):
                    pos = int(pos) if pos.isnumeric() else 9999
            label = None
            for p in labelprop:
                for _, _, candidate in g.triples((res2, p, None)):
                    if isinstance(candidate, Literal) and candidate.language in (
                        None,
                        "en",
                    ):  # hard-coded english for now
                        label = candidate
                        break
                if label:
                    break
                elif contextgraph:
                    for _, _, candidate in contextgraph.triples((res2, p, None)):
                        if isinstance(candidate, Literal) and candidate.language in (
                            None,
                            "en",
                        ):  # hard-coded english for now
                            label = candidate
                            break
                    if label:
                        break
            if label:
                results.append((label, res2, pos, _get_sortkey2(g, res2)))
            else:
                results.append((str(res2), res2, pos, _get_sortkey2(g, res2)))
        if max and len(results) >= max:
            break
    if havepos:
        try:
            results.sort(key=lambda x: x[2])
        except TypeError:  # protection against edge cases, leave unsorted then
            pass
    if abcsort:
        try:
            results.sort(key=lambda x: (x[0].lower(), x[3]))
        except TypeError:  # protection against edge cases, leave unsorted then
            pass
    return [tuple(x[:2]) for x in results]


def get_description(contextgraph: Graph, res: Union[URIRef, BNode, None]):
    """Gets the skos:note for a specific resource"""
    for _, _, candidate in contextgraph.triples((res, SKOS.note, None)):
        if isinstance(candidate, Literal) and candidate.language in (
            None,
            "en",
        ):  # hard-coded english for now
            return candidate
    return ""


def _get_sortkey2(g: Graph, res: Union[URIRef, BNode, None]):
    # set a secondary sort-key for items with the very same name
    # ensures certain interface types are listed before others in case of a tie
    if (res, RDF.type, SDO.WebApplication):
        return 0
    elif (res, RDF.type, SDO.WebSite) in g:
        return 1
    elif (res, RDF.type, SDO.WebPage) in g:
        return 3
    elif (res, RDF.type, SDO.WebAPI) in g:
        return 4
    elif (res, RDF.type, SDO.CommandLineApplication) in g:
        return 5
    else:
        return 9999


def get_index(g: Graph, restype=SDO.SoftwareSourceCode):
    groups = OrderedDict()
    for res, _, _ in g.triples((None, RDF.type, restype)):
        found = False
        label = g.value(res, SDO.name)
        if not label:
            label = g.value(res, SDO.identifier)
            if label:
                label = str(label).strip("/ \n").capitalize()
            else:
                label = "~untitled"

        for _, _, group in g.triples((res, SDO.applicationSuite, None)):
            groups.setdefault((str(group), True), []).append(
                (res, str(label))
            )  # explicit group
            found = True

        if not found:
            # ad-hoc group (singleton)
            group = str(label)
            groups.setdefault((group, False), []).append(
                (res, str(label))
            )  # ad-hoc group

    for key in groups:
        groups[key].sort(key=lambda x: x[1].lower())

    return sorted(
        ((k[0], k[1], v) for k, v in groups.items()), key=lambda x: x[0].lower()
    )


def is_resource(res) -> bool:
    return isinstance(res, (URIRef, BNode))


def get_badge(g: Graph, res: Union[URIRef, None], key):
    source = str(g.value(res, SDO.codeRepository)).strip("/")
    cleaned_url = source
    prefix = ""
    if source.startswith("https://"):
        repo_kind = codemeta.parsers.gitapi.get_repo_kind(source)
        git_address = cleaned_url.replace("https://", "").split("/")[0]
        prefix = "https://"
        git_suffix = cleaned_url.replace(prefix + git_address, "")[1:]
        if "github" == repo_kind:
            # github badges
            if key == "stars":
                yield f"https://img.shields.io/github/stars/{git_suffix}.svg?style=flat&color=5c7297", None, "Stars are an indicator of the popularity of this project on GitHub"
            elif key == "issues":
                # https://shields.io/category/issue-tracking
                yield f"https://img.shields.io/github/issues/{git_suffix}.svg?style=flat&color=5c7297", None, "The number of open issues on the issue tracker"
                yield f"https://img.shields.io/github/issues-closed/{git_suffix}.svg?style=flat&color=5c7297", None, "The number of closes issues on the issue tracker"
            elif key == "lastcommits":
                yield f"https://img.shields.io/github/last-commit/{git_suffix}.svg?style=flat&color=5c7297", None, "Last commit (main branch). Gives an indication of project development activity and rough indication of how up-to-date the latest release is."
                yield f"https://img.shields.io/github/commits-since/{git_suffix}/latest.svg?style=flat&color=5c7297&sort=semver", None, "Number of commits since the last release. Gives an indication of project development activity and rough indication of how up-to-date the latest release is."
        elif "gitlab" == repo_kind:
            # https://docs.gitlab.com/ee/api/project_badges.html
            # https://github.com/Naereen/badges
            if key == "lastcommits":
                # append all found badges at the end
                encoded_git_suffix = git_suffix.replace("/", "%2F")
                response = codemeta.parsers.gitapi.rate_limit_get(
                    f"{prefix}{git_address}/api/v4/projects/{encoded_git_suffix}/badges",
                    "gitlab",
                )
                if response:
                    response = response.json() #type: ignore
                    for badge in response:
                        if badge["kind"] == "project":
                            # or rendered_image_url field?
                            image_url = badge["image_url"]
                            name = badge["name"]
                            yield f"{image_url}", f"{name}", f"{name}"


def has_actionable_targetproducts(g: Graph, res: Union[URIRef, BNode]) -> bool:
    for _, _, targetres in g.triples((res, SDO.targetProduct, None)):
        if (targetres, SDO.url, None) in g:
            return True
    return False


def has_displayable_targetproducts(g: Graph, res: Union[URIRef, BNode]) -> bool:
    for _, _, targetres in g.triples((res, SDO.targetProduct, None)):
        if (
            (targetres, SDO.url, None) in g
            or (targetres, SDO.name, None) in g
            or (targetres, SOFTWARETYPES.executableName, None) in g
        ):
            return True
    return False


def type_label(g: Graph, res: Union[URIRef, None]) -> str:
    label = g.value(res, RDF.type)
    if label:
        label = str(label).split("/")[-1]
        return label
    else:
        return ""


def get_interface_types(
    g: Graph, res: Union[URIRef, None], contextgraph: Graph, fallback=False
):
    """Returns labels and definitions (2-tuple) for the interface types that this SoftwareSourceCode resource provides"""
    types = set()
    for _, _, res3 in g.triples((res, RDF.type, None)):
        if res3 != SDO.SoftwareSourceCode:
            stype = contextgraph.value(res3, RDFS.label)
            comment = contextgraph.value(res3, RDFS.comment)  # used for definitions
            if stype:
                types.add((stype, comment))
    for _, _, res2 in g.triples((res, SDO.targetProduct, None)):
        for _, _, res3 in g.triples((res2, RDF.type, None)):
            stype = contextgraph.value(res3, RDFS.label)
            comment = contextgraph.value(res3, RDFS.comment)  # used for definitions
            if stype:
                types.add((stype, comment))

    if not types and fallback:
        types.add(
            (
                "Unknown",
                "Sorry, we don't know what kind of interfaces this software provides. No interface types have been specified or could be automatically extracted.",
            )
        )
    return list(sorted(types))


def get_filters(
    g: Graph, res: Union[URIRef, None], contextgraph: Graph, json_filterables=False
) -> Union[str, list]:
    classes = defaultdict(set)
    sort_order = ["interfacetype", "developmentstatus", "category", "keywords"]
    for interfacetype, description in get_interface_types(
        g, res, contextgraph, fallback=True
    ):
        if json_filterables:
            classes["interfacetype"].add(slugify(interfacetype, "interfacetype"))
        else:
            classes["interfacetype"].add(
                (
                    slugify(interfacetype, "interfacetype"),
                    interfacetype,
                    description,
                    "Interface type",
                )
            )

    for _, _, devstatres in g.triples((res, CODEMETA.developmentStatus, None)):
        if json_filterables:
            classes["developmentstatus"].add(
                slugify(str(devstatres), "developmentstatus")
            )
        else:
            if (devstatres, SKOS.prefLabel, None) in contextgraph:
                devstatlabel = contextgraph.value(devstatres, SKOS.prefLabel)
            else:
                devstatlabel = str(devstatres)
            if (devstatres, SKOS.definition, None) in contextgraph:
                devstatdesc = contextgraph.value(devstatres, SKOS.definition)
            else:
                devstatdesc = ""
            classes["developmentstatus"].add(
                (
                    slugify(str(devstatres), "developmentstatus"),
                    devstatlabel,
                    devstatdesc,
                    "Development status",
                )
            )

    for _, _, catres in g.triples((res, SDO.applicationCategory, None)):
        if json_filterables:
            classes["category"].add(slugify(str(catres), "category"))
        else:
            if (catres, SKOS.prefLabel, None) in contextgraph:
                catlabel = contextgraph.value(catres, SKOS.prefLabel)
            else:
                catlabel = str(catres)
            if (catres, SKOS.definition, None) in contextgraph:
                catdesc = contextgraph.value(catres, SKOS.definition)
            else:
                catdesc = ""
            classes["category"].add(
                (slugify(str(catres), "category"), catlabel, catdesc, "Category")
            )

    for _, _, keyword in g.triples((res, SDO.keywords, None)):
        if json_filterables:
            classes["keywords"].add(slugify(str(keyword), "keyword"))
        else:
            classes["keywords"].add(
                (slugify(str(keyword), "keyword"), str(keyword).lower(), "", "Keywords")
            )

    if json_filterables:
        for key in classes:
            classes[key] = list( #type: ignore
                classes[key]
            )  # sets are not json serializable, so make it into a list
        return json.dumps(classes, ensure_ascii=False).replace('"', "'")
    else:
        for key in classes:
            l = list(classes[key])
            l.sort(key=lambda x: x[1])
            classes[key] = l #type: ignore

        return sorted(classes.items(), key=lambda x: sort_order.index(x[0]))


def slugify(s: str, prefix: str) -> str:
    slug = unicodedata.normalize("NFKD", s.lower())
    slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("-")
    slug = re.sub(r"[_]+", "_", slug)
    if len(slug) > 30:
        slug = md5(slug.encode("utf-8")).hexdigest()
    return prefix + "_" + slug


def get_target_platforms(g: Graph, res: Union[URIRef, None]):
    types = set()
    for label, _ in get_triples(g, res, SDO.runtimePlatform):
        label = label.lower().split(" ")[0]
        types.add(label.capitalize())
    for label, _ in get_triples(g, res, SDO.operatingSystem):
        label = label.lower().split(" ")[0]
        types.add(label.capitalize())
    return list(sorted(types))


def serialize_to_html(
    g: Graph,
    res: Union[Sequence, URIRef, None],
    args: AttribDict,
    contextgraph: Graph,
    sparql_query: Optional[str] = None,
    **kwargs,
) -> str:
    """Serialize to HTML with RDFa"""
    rootpath = sys.modules["codemeta2html"].__path__[0]
    env = Environment(
        loader=FileSystemLoader(os.path.join(rootpath, "templates")),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # env.policies['json.dumps_kwargs']['ensure_ascii'] = False
    # env.policies['json.dumps_function'] = to_json
    if res and not isinstance(res, (list, tuple)):
        assert isinstance(res, URIRef) or res is None
        if (res, RDF.type, SDO.SoftwareSourceCode) in g:
            template = "page_softwaresourcecode.html"
        elif (
            (res, RDF.type, SDO.SoftwareApplication) in g
            or (res, RDF.type, SDO.WebPage) in g
            or (res, RDF.type, SDO.WebSite) in g
            or (res, RDF.type, SDO.WebAPI) in g
            or (res, RDF.type, SOFTWARETYPES.CommandLineApplication) in g
            or (res, RDF.type, SOFTWARETYPES.SoftwareLibrary) in g
        ):
            template = "page_targetproduct.html"
        elif (res, RDF.type, SDO.Person) in g or (res, RDF.type, SDO.Organization):
            template = "page_person_or_org.html"
        else:
            template = "page_generic.html"
        index = []
    else:
        template = kwargs.get("indextemplate", "index.html")
        if isinstance(res, (list, tuple)):
            index = [
                ("Selected resource(s)", True, [(x, g.value(x, SDO.name)) for x in res])
            ]
            res = None
        elif sparql_query:
            index = query(g, sparql_query)
            index = [("Search results", True, index)]
        else:
            index = get_index(g)
    template = env.get_template(template)
    return template.render(
        g=g,
        res=res,
        SDO=SDO,
        CODEMETA=CODEMETA,
        CODEMETAPY=CODEMETAPY,
        RDF=RDF,
        RDFS=RDFS,
        STYPE=SOFTWARETYPES,
        SOFTWAREIODATA=SOFTWAREIODATA,
        REPOSTATUS=REPOSTATUS,
        SKOS=SKOS,
        TRL=TRL,
        get_triples=get_triples,
        get_description=get_description,
        get_target_platforms=get_target_platforms,
        type_label=type_label,
        styledir=args.styledir,
        css=args.css,
        contextgraph=contextgraph,
        URIRef=URIRef,
        get_badge=get_badge,
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        index=index,
        get_interface_types=get_interface_types,
        get_filters=get_filters,
        baseuri=args.baseuri,
        baseurl=args.baseurl,
        buildsite=args.buildsite,
        link_resource=link_resource,
        intro=args.intro,
        get_last_component=get_last_component,
        is_resource=is_resource,
        int=int,
        range=range,
        str=str,
        Literal=Literal,
        get_version=get_version,
        chain=chain,
        get_doi=get_doi,
        has_actionable_targetproducts=has_actionable_targetproducts,
        has_displayable_targetproducts=has_displayable_targetproducts,
        **kwargs,
    )


def to_json(o, **kwargs):
    result = json.dumps(o, ensure_ascii=False, indent=None)
    result.replace('"', "'")
    return result


def link_resource(g: Graph, res: URIRef, baseuri: Optional[str]) -> str:
    """produces a link to a resource page"""
    link = str(res)  # fallback
    if baseuri:
        link = str(res).replace(
            baseuri, ""
        )  # we remove the (absolute) baseuri and rely on baseurl set in html/head/base
    elif (res, SDO.identifier, None) in g:
        pos = str(res).find("/" + str(g.value(res, SDO.identifier)))
        if pos > -1:
            link = str(res)[pos + 1 :]
        elif str(res).startswith(("https://", "http://")):
            link = "/".join(str(res).split("/")[3:])
    if link and link[-1] != "/":
        link += "/"
    return link
