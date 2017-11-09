from distutils.core import setup
from pip.req import parse_requirements
install_reqs = parse_requirements("stars/requirements.txt", session="i")
requirements = [str(r.req) for r in install_reqs]
setup(
    name = 'stars',
    packages = [ 'stars' ],
    package_data = { 'stars' : [
        'requirements.txt'
    ]},
    version = '0.0.5',
    description = 'Stars Data Science Stack',
    author = 'Steve Cox',
    author_email = 'scox@renci.org',
    install_requires =
        requirements + ['requests-toolbelt==0.8.0'],
    dependency_links = [
        'https://github.com/requests/toolbelt/archive/91f076e8170fa89e84d20cb2567e48e2b6c56929.zip#egg=requests_toolbelt-0.0.8+git.91f076e'
    ],
    include_package_data=True,
    url = 'https://github.com/stevencox/stars',
    download_url = 'http://github.com/stevencox/stars/archive/0.1.tar.gz',
    keywords = [ 'spark', 'mesos', 'zeppelin', 'jupyter', 'blazegraph' ],
    classifiers = [ ],
    entry_points = {
        'console_scripts': [
            'data-commons = stars.data_commons:main'
        ]
    }
)
