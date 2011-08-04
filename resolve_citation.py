import mechanize
import os
import re
import errno
import urllib
import urllib2

FAKE_USER_AGENT = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; '
                    'rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
#    br.set_debug_http(True)
#    br.set_debug_redirects(True)
#    br.set_debug_responses(True)
class ScrapingBrokenError(Exception):
    pass

_scrapers = {}
def scraper(uripart):
    def decorator(func):
        _scrapers[uripart] = func
        return func
    return decorator

def assert_bibtex_contains(sub, whole):
    if sub not in whole:
        raise ScrapingBrokenError("Did not succeed in retrieving BIBTEX for %s" % doi)
    
@scraper('sciencedirect.com')
def scrape_sciencedirect(br, doi, response):
    response = br.follow_link(text_regex="Export citation")
    br.select_form('exportCite')
    br['citation-type'] = ['BIBTEX']
    response = br.submit()
    bibtex = response.read()
    assert_bibtex_contains('@article', bibtex)
    return bibtex

@scraper('siam.org')
def scrape_siam(br, doi, response):
    # Uses Javascript to present the link... we grep the HTML for an ID
    # to embed in an URL. FRAGILE!
    html = response.read()
    m = re.search(r"constructArticleDLbox_pol\('Download', '([0-9.]+)'\)", html)
    if m is None:
        raise ScrapingBrokenError()
    bib_url = ('http://epubs.siam.org/modules/getCitation.jsp?view=BINARY&'
               'contentid=%s&format=BIBTEX&Submit=Download' % m.group(1))
    bibtex = br.open(bib_url).read()
    bibtex = bibtex.replace('@journal article', '@article')
    assert_bibtex_contains('@article', bibtex)
    return bibtex

def fetch_bibtex_of_doi(uri):
    url = 'http://dx.doi.org/' + uri[len('doi:'):]
    br = mechanize.Browser()
    br.set_handle_robots(False)
    br.addheaders = FAKE_USER_AGENT
    response = br.open(url)
    redirected_url = response.geturl()
    for key, func in _scrapers.iteritems():
        if key in redirected_url:
            return func(br, uri, response)
    else:
        raise NotImplementedError("Does not know how to handle %s" % response.geturl())

def fetch_bibtex_of_arxiv(uri):
    raise NotImplementedError()

def fetch_bibtex_of_uri(uri):
    if uri.startswith('doi:'):
        return fetch_bibtex_of_doi(uri)
    elif uri.startswith('arXiv:'):
        return fetch_bibtex_of_arxiv(uri)
    else:
        raise NotImplementedError("Does not know how to handle URI scheme of %s" % uri)

class CitationResolver():
    def __init__(self, cachedir=None):
        if cachedir is None:
            cachedir = os.path.expanduser('~/.autobib')
        self.cachedir = os.path.abspath(cachedir)

    def fetch_bibtex_of_doi(self, doi):
        if not doi.startswith('doi:'):
            raise ValueError("Invalid DOI URI, lacks doi: prefix")
        path = os.path.join(self.cachedir,
                            doi[4:].replace('/', os.path.pathsep).replace(':', '_'),
                            'bibtex.txt')
        if not os.path.exists(path):
            bibtex = fetch_bibtex_of_doi(doi)
            try:
                os.makedirs(os.path.dirname(path))
            except OSError:
                if os.errno == errno.EEXIST:
                    pass
            with file(path, 'w') as f:
                f.write(bibtex)
        else:
            with file(path) as f:
                bibtex = f.read()
        return bibtex

    


    
def test():
#    print fetch_bibtex_of_doi('doi:10.1016/j.jcp.2010.05.004')
#    print fetch_bibtex_of_doi('doi:10.1137/030602678')
    print fetch_bibtex_of_uri('doi:10.1051/0004-6361/201015906') #'arxiv:1010.2084'

if __name__ == '__main__':
    test()
