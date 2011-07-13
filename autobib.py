import re
import sys
from StringIO import StringIO
from pybtex.database.input import bibtex

from resolve_citation import CitationResolver

def fetch_reference(uri):
    bibtex_str = CitationResolver().fetch_bibtex_of_doi(uri)
    parser = bibtex.Parser()
    bib_data = parser.parse_stream(StringIO(bibtex_str))
    if len(bib_data.entries) != 1:
        raise AssertionError()
    entry = bib_data.entries.values()[0]
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
    formatter = ApjFormatter()
    authorlist = [formatter.format_author(a) for a in entry.persons['author']]
    assert len(authorlist) > 0
    if len(authorlist) > 1:
        authorlist[-1] = '\& %s' % authorlist[-1]
    authorlist = ', '.join(authorlist)
    fields = entry.fields
    lastname = entry.persons['author'][0].last()[0]
    return ('\\bibitem[{lastname}({fields[year]})]{{{tag}}}\n'
            '  {authorlist} {fields[year]} {fields[journal]}, '
            '{fields[volume]}, {fields[number]}\n').format(**locals())
    

CITES_RE = re.compile(r'\\cite\S*{([^}]+)}', re.DOTALL)
#DOI_RE = re.compile(r'\cite\S*{doi:[^,}]*')
AUTOBIB_SECTION_RE = re.compile(r'^%autobib start$.*^%autobib stop$',
                                re.MULTILINE | re.DOTALL)
AUTOBIB_CONFIG_RE = re.compile(r'^%autobib\s+(.*)$', re.MULTILINE)

def transform_tex(tex):
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
                  if ref.startswith('doi:')]
    references = set(references)
    def get_tag(uri):
        return reverse_aliases.get(uri, uri)
    formatted_references = [format_citation_apj(uri, get_tag(uri))
                            for uri in references]
    
    refsection = '\n'.join(formatted_references)

    print refsection
    tex = AUTOBIB_SECTION_RE.sub('%autobib start\n' +
                                 refsection.replace('\\', '\\\\') +
                                 '%autobib stop',
                                 tex)
    return tex

def test():
    print format_citation_apj('doi:10.1016/j.acha.2009.08.005')
    #print format_citation_apj('doi:10.1016/j.jcp.2010.05.004')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('texname', default=None)
    args = parser.parse_args()
    with file(args.texname) as f:
        tex = f.read()
    tex = transform_tex(tex)
    with file(args.texname, 'w') as f:
        f.write(tex)




