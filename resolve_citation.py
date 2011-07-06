import mechanize

FAKE_USER_AGENT = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; '
                    'rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
#    br.set_debug_http(True)
#    br.set_debug_redirects(True)
#    br.set_debug_responses(True)

def handle_sciencedirect(br, doi):
    response = br.follow_link(text_regex="Export citation")
    br.select_form('exportCite')
    br['citation-type'] = ['BIBTEX']
    response = br.submit()
    bibtex = response.read()
    if '@article' not in bibtex:
        raise Exception("Did not succeed in retrieving BIBTEX for %s" % doi)
    return bibtex

def fetch_bibtex_of_doi(doi):
    if not doi.startswith('doi:'):
        raise ValueError("Invalid DOI URI, lacks doi: prefix")
    url = 'http://dx.doi.org/' + doi[4:]
    br = mechanize.Browser()
    br.set_handle_robots(False)
    br.addheaders = FAKE_USER_AGENT
    response = br.open(url)
    if 'sciencedirect.com' in response.geturl():
        return handle_sciencedirect(br, doi)
    else:
        raise ValueError("Does not know how to handle %s" % response.geturl())
    
def test():
    print fetch_bibtex_of_doi('doi:10.1016/j.jcp.2010.05.004')

if __name__ == '__main__':
    test()
