# sz-python-tools

If you are beginning your journey with [Senzing],
please start with [Senzing Quick Start guides].

You are in the [Senzing Garage] where projects are "tinkered" on.
Although this GitHub repository may help you understand an approach to using Senzing,
it's not considered to be "production ready" and is not considered to be part of the Senzing product.
Heck, it may not even be appropriate for your application of Senzing!

## :warning: WARNING: template-python is still in development :warning: _

At the moment, this is "work-in-progress" with Semantic Versions of `0.n.x`.
Although it can be reviewed and commented on,
the recommendation is not to use it yet.

## Synopsis

This section should give 1-2 sentences on what the artifacts in this repository do.

[![Python 3.11 Badge]][Python 3.11]
[![PEP8 Badge]][PEP8]
[![PyPI version Badge]][PyPi version]
[![Downloads Badge]][Downloads]
[![License Badge]][License]
[![Coverage Badge]][Coverage]

## Overview

This section should be replaced with real "**Overview**" content after initial repository creation.

This repository (template-python) contains exemplar python scripts that can be used to start a new python project.

The [template-python.py] python script is a boilerplate which has the following features:

1. Conforms to [PEP-0008] python programming style guide.
    1. With exception of some lines being too long.
1. "command subcommand" command line.
1. A structured command line parser and "-help"
1. Configuration via:
    1. Command line options
    1. Environment variables
    1. Configuration file
    1. Default
1. Messages dictionary
1. Logging and Log Level support.
1. Entry / Exit log messages.
1. Docker support.

## Use

### Configuration

Configuration values specified by environment variable or command line parameter.

- **[SENZING_DATABASE_URL]**
- **[SENZING_DEBUG]**

## References

1. [Development]
1. [Errors]
1. [Examples]
1. Related artifacts:
    1. [DockerHub]

[Coverage badge]: https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fsenzing-garage%2Fsz-sdk-python%2Fpython-coverage-comment-action-data%2Fendpoint.json
[Coverage]: https://htmlpreview.github.io/?https://github.com/senzing-garage/template-python/blob/python-coverage-comment-action-data/htmlcov/index.html
[Development]: docs/development.md
[DockerHub]: https://hub.docker.com/r/senzing/template-python
[Downloads Badge]: https://static.pepy.tech/badge/template-python
[Downloads]: https://pepy.tech/project/template-python
[Errors]: docs/errors.md
[Examples]: docs/examples.md
[License Badge]: https://img.shields.io/badge/License-Apache2-brightgreen.svg
[License]: https://github.com/senzing-garage/template-python/blob/main/LICENSE
[PEP-0008]: https://github.com/senzing-garage/knowledge-base/blob/main/WHATIS/pep-0008.md
[PEP8 Badge]: https://img.shields.io/badge/code%20style-pep8-orange.svg
[PEP8]: https://www.python.org/dev/peps/pep-0008/
[PyPI version Badge]: https://badge.fury.io/py/template-python.svg
[PyPi version]: https://badge.fury.io/py/template-python
[Python 3.11 Badge]: https://img.shields.io/badge/python-3.11-blue.svg
[Python 3.11]: https://www.python.org/downloads/release/python-3110/
[Senzing Garage]: https://github.com/senzing-garage
[Senzing Quick Start guides]: https://docs.senzing.com/quickstart/
[SENZING_DATABASE_URL]: https://github.com/senzing-garage/knowledge-base/blob/main/lists/environment-variables.md#senzing_database_url
[SENZING_DEBUG]: https://github.com/senzing-garage/knowledge-base/blob/main/lists/environment-variables.md#senzing_debug
[Senzing]: https://senzing.com/
[template-python.py]: template-python.py
