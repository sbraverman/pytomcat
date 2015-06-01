import os
import sys
from CustomInstall import CustomInstall
from setuptools import setup, Command

install_requires = [
  ]

tests_require = [
  ]

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "PyTomcat",
    version = "1.0",
    author = "Dun and Bradstreet",
    author_email = "pytomcat@dandb.com",
    description = ("Management of Apache Tomcat via Python"),
    license = "GPLv3",
    keywords = "python tomcat ",
    url = "https://github.com/dandb/pytomcat",
    packages=['pytomcat'],
    install_requires = install_requires,
    tests_require = tests_require,
    extras_require={'test': tests_require},
    long_description=read('README.md') + '\n\n' + read('CHANGES'),
    test_suite = 'tests',
    cmdclass={'install': CustomInstall},
)
