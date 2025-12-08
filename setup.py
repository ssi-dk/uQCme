#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Setup configuration for uQCme"""

import os
from setuptools import setup, find_packages

# Read version from __init__.py
here = os.path.abspath(os.path.dirname(__file__))
about = {}
with open(os.path.join(here, 'src', 'uQCme', '__init__.py')) as f:
    exec(f.read(), about)

# Read long description from README
with open(os.path.join(here, 'README.md'), 'r') as f:
    long_description = f.read()

# Requirements
install_requires = [
    'streamlit>=1.28.0',
    'pandas>=1.5.0',
    'plotly>=5.15.0',
    'pyyaml>=6.0',
    'openpyxl>=3.0.0',
    'pydantic>=2.0.0',
    'pandera>=0.18.0',
]

tests_require = [
    'pytest>=7.0.0',
    'pytest-cov>=4.0.0',
]

setup(
    name='uqcme',
    version=about['__version__'],
    description='Microbial Quality Control Dashboard',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='SSI-DK',
    author_email='kimn@ssi.dk',
    url='https://github.com/ssi-dk/uQCme',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    include_package_data=True,
    package_data={
        'uQCme': ['defaults/*'],
    },
    python_requires='>=3.12,<3.13',
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        'test': tests_require,
        'dev': tests_require + [
            'flake8',
            'black',
        ],
    },
    entry_points={
        'console_scripts': [
            'uqcme=uQCme.cli.main:main',
            'uqcme-dashboard=uQCme.app.main:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.12',
        'License :: OSI Approved :: MIT License',
    ],
    keywords='microbial qc quality-control bioinformatics',
)
