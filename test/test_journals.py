from nose.tools import eq_, ok_
from textwrap import dedent

from resolve_citation import *

def test_AA():
    bibtex = fetch_bibtex_of_uri('doi:10.1051/0004-6361/201015906')
    print bibtex
    ok_('Libpsht' in bibtex)
    ok_('Reinecke' in bibtex)

def test_ApJ():
    bibtex = fetch_bibtex_of_uri('doi:10.1086/507692')
    print bibtex
    
