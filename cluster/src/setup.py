from distutils.core import setup
from pip.req import parse_requirements
install_reqs = parse_requirements("stars/requirements.txt", session="i")
requirements = [str(r.req) for r in install_reqs]
setup(
    name = 'stars',
    packages = [ 'stars' ],
    package_data={ 'stars' : [
        'requirements.txt'
    ]},
    version = '0.0.5',
    description = 'Stars Data Science Stack',
    author = 'Steve Cox',
    author_email = 'scox@renci.org',
    install_requires = requirements,
    include_package_data=True,
    url = 'https://github.com/stevencox/stars',
    download_url = 'http://github.com/stevencox/stars/archive/0.1.tar.gz',
    keywords = [ 'spark', 'mesos', 'zeppelin', 'jupyter', 'blazegraph' ],
    classifiers = [ ],
)
