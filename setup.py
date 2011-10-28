#!/usr/bin/env python

from setuptools import setup
from os.path import join, dirname

try:
    long_description = open(join(dirname(__file__), 'README.rst')).read()
except Exception:
    long_description = None

setup(
    name='asynchttp',
    version='0.0.4',
    description='A simple httplib2 based asynchronous HTTP library for python',
    author='Ross McFarland',
    author_email='ross@gmail.com',
    url='http://github.com/ross/python-asynchttp',

    long_description=long_description,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],

    packages=['asynchttp'],
    provides=['asynchttp'],
    requires=['httplib2(>=0.5.0)'],
    install_requires=['httplib2>=0.5.0'],
)
