from nose.tools import eq_, ok_
from textwrap import dedent

from resolve_citation import *

def test_AA():
    bibtex = fetch_bibtex_of_uri('doi:10.1051/0004-6361/201015906')
    ok_('Libphst' in bibtex and 'Reinecke' in bibtex)

