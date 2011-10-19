#encoding: utf-8

import re
import sys
from StringIO import StringIO
from pybtex.database.input import bibtex
from pprint import pprint

from resolve_citation import CitationResolver

ISSN_DB = {
    '10648275': 'SIAM J. Sci. Comput.',
    '00361429': 'SIAM J. Numer. Anal.'    
}

def issn_to_journal(issn):
    try:
        return ISSN_DB[issn]
    except KeyError:
        raise NotImplementedError('Please register ISSN %s in ISSN_DB' % issn)

def fetch_reference(uri):
    bibtex_str = CitationResolver().fetch_bibtex_of_doi(uri)
    bibtex_str = massage_bibtex_string(bibtex_str)
    parser = bibtex.Parser()
    bib_data = parser.parse_stream(StringIO(bibtex_str))
    if len(bib_data.entries) != 1:
        raise AssertionError()
    entry = bib_data.entries.values()[0]
    return entry

def massage_bibtex_string(bibtex):
    if 'journal = {A\\&A}' in bibtex:
        # TODO: Only on author field?
        bibtex = bibtex.replace('{{', '{').replace('}}', '}')
    return bibtex

def massage_bibtex_entry(entry):
    if 'journal' not in entry.fields:
        try:
            entry.fields['journal'] = issn_to_journal(entry.fields['issn'])
        except NotImplementedError:
            pprint(entry.fields)
            raise
    if entry.fields['journal'] == 'A\\&A':
        entry.fields['number'] = entry.fields['pages']
        if len(entry.persons['author']) > 1:
            raise NotImplementedError(
                'Please fix massage_bibtex_string for more than one author')
    if 'number' not in entry.fields:
        entry.fields['number'] = entry.fields['issue']
    return entry

class ApjFormatter(object):
    def format_author(self, author):
        x = []
        x.extend(author.last())
        x.extend(author.first(abbr=True))
        x.extend(author.middle(abbr=True))
        return ', '.join(x)

def format_citation_apj(uri, tag):
    entry = fetch_reference(uri)
    entry = massage_bibtex_entry(entry)
    formatter = ApjFormatter()
    authorlist = [formatter.format_author(a) for a in entry.persons['author']]
    assert len(authorlist) > 0
    many_authors = len(authorlist) > 1
    if len(authorlist) > 1:
        authorlist[-1] = '\& %s' % authorlist[-1]
    authorlist_str = ', '.join(authorlist)
    fields = entry.fields
    lastname = entry.persons['author'][0].last()[0]
    etal = ' et al.' if many_authors else ''
    sort_key = authorlist_str
    return (sort_key, ('\\bibitem[{lastname}{etal}({fields[year]})]{{{tag}}}\n'
             '  {authorlist_str} {fields[year]} {fields[journal]}, '
             '{fields[volume]}, {fields[number]}\n').format(**locals()))
    

CITES_RE = re.compile(r'\\cite\S*{([^}]+)}', re.DOTALL)
#DOI_RE = re.compile(r'\cite\S*{doi:[^,}]*')
AUTOBIB_SECTION_RE = re.compile(r'^%autobib start$.*^%autobib stop$',
                                re.MULTILINE | re.DOTALL)
AUTOBIB_CONFIG_RE = re.compile(r'^%autobib\s+(.*)$', re.MULTILINE)

def transform_tex(tex, logger):
    # Parse settings
    aliases = {}
    for expr in AUTOBIB_CONFIG_RE.findall(tex):
        expr = expr.strip()
        if expr in ('start', 'stop'):
            pass
        elif expr.startswith('let '):
            alias, uri = expr[4:].split('=')
            aliases[alias] = uri
        else:
            raise Exception("Invalid setting: %%autobib %s" % expr)
    reverse_aliases = dict((value, key) for key, value in aliases.iteritems())

    # Scan for journal references
    references = aliases.values()
    references.extend(sum([expr.split(',') for expr in CITES_RE.findall(tex)],
                          []))
    references = [ref.strip() for ref in references
                  if ref.strip().startswith('doi:')]
    references = set(references)

    citation_replacements = []
    formatted_references = []
    for uri in references:
        # Patch references with invalid characters in them
        if uri.startswith('doi:10.1016/S0377'):
            tag = uri
            if not re.match(r'doi:10.1016/S0377-\d{4}\(?\d\d\)?\d{5}-\d', uri):
                raise ValueError('Unexpected URI for domain doi:10.1016/S0377: %s' % uri)
            if '(' in uri:
                logger.info('Patching citation: Removing paranthesis in %s' % uri)
                tag = uri.replace('(', '').replace(')', '')
                citation_replacements.append((uri, tag))
            else:
                # The uri was already patched&replaced in a previous scan, reinsert (
                i = len('doi:10.1016/S0377-0000')
                j = 2
                uri = '%s(%s)%s' % (uri[:i], uri[i:i + j], uri[i + j:])
        else:
            tag = reverse_aliases.get(uri, uri)
        # Make references
        try:
            sort_key, citation = format_citation_apj(uri, tag)
        except NotImplementedError, e:
            print e
            pass
        else:
            formatted_references.append((sort_key, citation))

    formatted_references.sort()
    
    # Do citation replacements
    for old, new in citation_replacements:
        tex = tex.replace(old, new)

    # Insert references in tex
    refsection = u'\n'.join(text for sort, text in formatted_references)
    tex = AUTOBIB_SECTION_RE.sub(u'%autobib start\n' +
                                 refsection.replace('\\', '\\\\') +
                                 u'%autobib stop',
                                 tex)
    return tex

def test():
    print format_citation_apj('doi:10.1016/j.acha.2009.08.005')
    #print format_citation_apj('doi:10.1016/j.jcp.2010.05.004')

if __name__ == '__main__':
    import argparse
    import logging
    logging.basicConfig()
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument('texname', default=None)
    args = parser.parse_args()
    with file(args.texname) as f:
        tex = f.read().decode('utf-8')
    tex = transform_tex(tex, logger)
    with file(args.texname, 'w') as f:
        f.write(tex.encode('utf-8'))




