"-"
from distutils.core import setup

setup(
    name='gigaspoon',
    version='0.1.0',
    packages=['gigaspoon'],
    extras_require={
        "dev": ["pytest", "pytest-cov"],
        "flask": ["flask"],
        "sqlalchemy": ["sqlalchemy"],
    })
