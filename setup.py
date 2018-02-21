"-"
from distutils.core import setup

setup(
    name='spudbucket',
    version='0.1.0',
    packages=['spudbucket'],
    install_requires=['flask'],
    extras_require={
        "dev": ["pytest"]
    })
