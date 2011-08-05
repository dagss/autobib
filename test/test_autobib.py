from nose.tools import eq_, ok_
from textwrap import dedent

from autobib import transform_tex

class MockLogger:
    def __init__(self):
        self.messages = []
    def info(self, msg):
        self.messages.append('INFO %s' % msg)

def dedent_eq(x, y):
    eq_(dedent(x), dedent(y))

def check_transform(input, output, log=''):
    expected_log = [x.strip() for x in log.splitlines() if x.strip() != '']
    logger = MockLogger()
    tex = transform_tex(dedent(input), logger)
    eq_(dedent(output), tex)
    eq_(expected_log, logger.messages)

def test_doi_with_parens():
    check_transform(input=r'''
    \cite{doi:10.1016/S0377-0427(03)00546-6}
    %autobib start
    %autobib stop
    ''', output=r'''
    \cite{doi:10.1016/S0377-04270300546-6}
    %autobib start
    \bibitem[Kunis et al.(2003)]{doi:10.1016/S0377-04270300546-6}
      Kunis, S., \& Potts, D. 2003 Journal of Computational and Applied Mathematics, 161, 1
    %autobib stop
    ''', log='''
    INFO Patching citation: Removing paranthesis in doi:10.1016/S0377-0427(03)00546-6
    ''')

    check_transform(input=r'''
    \cite{doi:10.1016/S0377-04270300546-6}
    %autobib start
    %autobib stop
    ''', output=r'''
    \cite{doi:10.1016/S0377-04270300546-6}
    %autobib start
    \bibitem[Kunis et al.(2003)]{doi:10.1016/S0377-04270300546-6}
      Kunis, S., \& Potts, D. 2003 Journal of Computational and Applied Mathematics, 161, 1
    %autobib stop
    ''', log='''
    ''')

