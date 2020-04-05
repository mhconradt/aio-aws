[![pipeline status](https://gitlab.com/dazza-codes/aio-aws/badges/master/pipeline.svg)](https://gitlab.com/dazza-codes/aio-aws/-/commits/master)
[![coverage report](https://gitlab.com/dazza-codes/aio-aws/badges/master/coverage.svg)](https://gitlab.com/dazza-codes/aio-aws/-/commits/master)

# aio-aws

Asynchronous functions and tools for AWS services.  There is a
limited focus on s3 and AWS Batch.  Additional services could be
added, but this project is likely to retain a limited focus.
For general client solutions, see
[aioboto3](https://github.com/terrycain/aioboto3) and
[aiobotocore](https://github.com/aio-libs/aiobotocore), which wrap 
[botocore](https://botocore.amazonaws.com/v1/documentation/api/latest/index.html)

The API documentation is published as gitlab pages at:
- http://dazza-codes.gitlab.io/aio-aws

# Getting Started

To use the source code, it can be cloned directly. To
contribute to the project, first fork it and clone the forked repository.

The following setup assumes that
[miniconda3](https://docs.conda.io/en/latest/miniconda.html) and
[poetry](https://python-poetry.org/docs/) are installed already
(and `make` 4.x).

- https://docs.conda.io/en/latest/miniconda.html
    - recommended for creating virtual environments with required versions of python
- https://python-poetry.org/docs/
    - recommended for managing a python project with pip dependencies for
      both the project itself and development dependencies

```shell
git clone https://gitlab.com/dazza-codes/aio-aws
cd aio-aws
conda create -n aio-aws python=3.6
conda activate aio-aws
make init  # calls poetry install
```

# Install

This project has a very limited focus.  For general client solutions, see
[aioboto3](https://github.com/terrycain/aioboto3) and
[aiobotocore](https://github.com/aio-libs/aiobotocore), which wrap 
[botocore](https://botocore.amazonaws.com/v1/documentation/api/latest/index.html)
to patch it with features for async coroutines using
[aiohttp](https://aiohttp.readthedocs.io/en/latest/) and
[asyncio](https://docs.python.org/3/library/asyncio.html).
This project is not published as a pypi package because there is no promise
to support or develop it extensively, at this time.  For the curious, it
can be used directly from a gitlab tag.  Note that any 0.x releases are
likely to have breaking API changes.

## pip

pip can install packages using a
[git protocol](https://pip.pypa.io/en/stable/reference/pip_install/#git).

```shell
pip install -U "git+https://gitlab.com/dazza-codes/aio-aws.git#egg=aio-aws"
pip check  # might not guarantee consistent packages
# use git refs
pip install -U "git+https://gitlab.com/dazza-codes/aio-aws.git@master#egg=aio-aws"
pip install -U "git+https://gitlab.com/dazza-codes/aio-aws.git@0.1.0#egg=aio-aws"
```

## poetry

```shell
poetry add "git+https://gitlab.com/dazza-codes/aio-aws.git"
pip check  # poetry will try to guarantee consistent packages or fail
```

```toml
# pyproject.toml snippet

[tool.poetry.dependencies]
python = "^3.6"
aio-aws = {git = "https://gitlab.com/dazza-codes/aio-aws.git"}
# Or use a tagged release - recommended
# aio-aws = {git = "https://gitlab.com/dazza-codes/aio-aws.git", tag = "0.1.0"}
```

# License

```text
Copyright 2019-2020 Darren Weber

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

# Notices

This project is inspired by and uses various open source projects that use
the Apache 2 license, including but not limited to:
- Apache Airflow: https://github.com/apache/airflow
- aiobotocore: https://github.com/aio-libs/aiobotocore
- botocore: https://github.com/boto/botocore
