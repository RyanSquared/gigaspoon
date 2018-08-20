"-"
from distutils.core import setup

setup(
    name='gigaspoon',
    version='0.1.0',
    packages=['gigaspoon'],
    install_requires=['flask'],
    extras_require={
        "dev": ["pytest", "pytest-cov"]
    })
