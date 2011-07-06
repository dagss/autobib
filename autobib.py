
from StringIO import StringIO
from pybtex.database.input import bibtex

from resolve_citation import fetch_bibtex_of_doi

def fetch_reference(uri):
    bibtex_str = fetch_bibtex_of_doi(uri)
    parser = bibtex.Parser()
    bib_data = parser.parse_stream(StringIO(bibtex_str))
    if len(bib_data.entries) != 1:
        raise AssertionError()
    entry = bib_data.entries.values()[0]
    return entry

class ApjFormatter(object):
    def format_author(self, author):
        print author
        x = author.last()
        x.extend(author.first(abbr=True))
        x.extend(author.middle(abbr=True))
        return ', '.join(x)

def format_citation_apj(uri):
    entry = fetch_reference(uri)
    formatter = ApjFormatter()
    authorpart = [formatter.format_author(a) for a in entry.persons['author']]
    assert len(authorpart) == 1
    authorpart = ','.join(authorpart)
    fields = entry.fields
    journal = fields['journal']
    return ('{authorpart} {fields[year]} {journal}, '
            '{fields[volume]}, {fields[number]}').format(**locals())
    
        

def test():
    print format_citation_apj('doi:10.1016/j.jcp.2010.05.004')

if __name__ == '__main__':
    test()
