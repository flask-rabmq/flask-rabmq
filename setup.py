import codecs
import os

try:
    from setuptools import setup
except:
    from distutils.core import setup


def read(fname):
    return codecs.open(os.path.join(os.path.dirname(__file__), fname)).read()


NAME = "flask_rabmq"

PACKAGES = ["flask_rabmq", ]


DESCRIPTION = "Adds Rabbitmq support to your Flask application."

LONG_DESCRIPTION = read("README.md")
LONG_DESCRIPTION_CONTENT_TYPE = 'text/markdown'

KEYWORDS = "python flask Rabbitmq"

AUTHOR = "chenxiaolong"

AUTHOR_EMAIL = "cxiaolong6@gmail.com"


URL = 'https://github.com/flask-rabmq/flask-rabmq'

VERSION = "0.0.22"

LICENSE = "MIT"

INSTALL_REQUIRES = ["Flask>=0.10", "kombu>=4.2.0"]

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type=LONG_DESCRIPTION_CONTENT_TYPE,
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
    ],
    keywords=KEYWORDS,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    url=URL,
    license=LICENSE,
    install_requires=INSTALL_REQUIRES,
    packages=PACKAGES,
    include_package_data=True,
    zip_safe=True,
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*",
)
