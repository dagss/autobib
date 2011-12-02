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
    if 'journal' not in entry.fields and 'issn' in entry.fields:
        try:
            entry.fields['journal'] = issn_to_journal(entry.fields['issn'])
        except NotImplementedError:
            pprint(entry.fields)
            raise
    if entry.fields.get('journal', None) == 'A\\&A':
        entry.fields['number'] = entry.fields['pages']
        if len(entry.persons['author']) > 1:
            raise NotImplementedError(
                'Please fix massage_bibtex_string for more than one author')
    if 'number' not in entry.fields:
        if 'issue' in entry.fields:
            entry.fields['number'] = entry.fields['issue']
    return entry

class ApjFormatter(object):

    journal_abbreviations = {
        'Astron.Astrophys.' : 'A\&A',
        'The Astrophysical Journal' : 'ApJ'
        }
    
    def format_author(self, author):
        letters = []
        # First names can be either a full name, A.B., or A. B.
        for x in author.first() + author.middle():
            for y in x.split('.'):
                y = y.strip()
                if len(y) > 0:
                    letters.append(y[0] + '.')
        if len(author.last()) != 1:
            raise NotImplementedError("Author list: %r" % author.last())
        r = '%s, %s' % (author.last()[0], ' '.join(letters))
        return r

    def get_journal_name(self, entry):
        if 'journal' not in entry.fields:
            return None
        journal = entry.fields['journal']
        journal = self.journal_abbreviations.get(journal, journal)
        print journal
        return journal

def utf8_to_latex(s):
    s = s.replace(u'ó', "\\'o")
    return s

def format_citation_apj(uri, tag):
    entry = fetch_reference(uri)
    entry = massage_bibtex_entry(entry)
    formatter = ApjFormatter()
    authorlist = [formatter.format_author(a) for a in entry.persons['author']]
    assert len(authorlist) > 0
    if len(authorlist) > 1:
        authorlist[-1] = '\& %s' % authorlist[-1]
    authorlist_str = ', '.join(authorlist)
    fields = entry.fields

    if len(authorlist) == 2:
        citation = ' \& '.join([author.last()[0] for author in entry.persons['author']])
    else:
        citation = entry.persons['author'][0].last()[0]
        if len(authorlist) > 1:
            citation += ' et al.'

    journal = formatter.get_journal_name(entry)
    if journal is None:
        publication = fields['title']
    else:
        number = ',~' + fields['number'] if 'number' in fields else ''
        publication = '%s,~%s%s' % (journal, fields['volume'], number)
    
    lastname = entry.persons['author'][0].last()[0]
    sort_key = authorlist_str
    s = (u'\\bibitem[{citation}({fields[year]})]{{{tag}}}\n'
         '  {authorlist_str} {fields[year]} {publication}\n').format(**locals())
    s = utf8_to_latex(s)
    return (sort_key, s)
    

CITES_RE = re.compile(r'\\cite\S*{([^}]+)}', re.DOTALL)
#DOI_RE = re.compile(r'\cite\S*{doi:[^,}]*')
AUTOBIB_SECTION_RE = re.compile(r'^%autobib start$.*^%autobib stop$',
                                re.MULTILINE | re.DOTALL)
AUTOBIB_CONFIG_RE = re.compile(r'^%autobib (let)\s+(.*)$', re.MULTILINE)
AUTOBIB_MANUAL_RE = re.compile(r'^%autobib manual start$(.*)^%autobib manual stop$',
                                re.MULTILINE | re.DOTALL)

def transform_tex(tex, logger):
    # Parse settings
    aliases = {}
    for command, expr in AUTOBIB_CONFIG_RE.findall(tex):
        if command == 'let':
            alias, uri = expr.split('=')
            aliases[alias] = uri
        else:
            raise Exception("Invalid setting: %%autobib %s" % expr)
    reverse_aliases = dict((value, key) for key, value in aliases.iteritems())

    # Scan for insertions -- that is, manual references that must be
    # inserted in the right place alphabetically
    insertions = []
    current_insertion_lines = []
    current_key = None
    def commit_insertion():
        if current_key is not None:
            insertions.append((current_key, '\n'.join(current_insertion_lines) + '\n'))
            del current_insertion_lines[:]
    for expr in AUTOBIB_MANUAL_RE.findall(tex):
        lines = expr.split('\n')
        for line in lines:
            line = line.strip()
            if line == '':
                continue
            if not line.startswith(u'%'):
                raise NotImplementedError("Insertion line does not start with %")
            line = line[1:].strip()
            if line.startswith(u'\\bibitem['):
                commit_insertion()
                current_key = line[len(u'\\bibitem['):]
            current_insertion_lines.append(line)
    commit_insertion()

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

    formatted_references.extend(insertions)
    formatted_references.sort()

    
    # Do citation replacements
    for old, new in citation_replacements:
        tex = tex.replace(old, new)

    # Insert references in tex
    refsection = u'\n'.join(text for sort, text in formatted_references)

    if not AUTOBIB_SECTION_RE.search(tex):
        raise Exception("No autobib section found in tex!")
        
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




