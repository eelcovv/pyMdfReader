.. These are examples of badges you might want to add to your README:
please update the URLs accordingly

    .. image:: https://api.cirrus-ci.com/github/<USER>/pyMdfReader.svg?branch=main
        :alt: Built Status
        :target: https://cirrus-ci.com/github/<USER>/pyMdfReader
    .. image:: https://readthedocs.org/projects/pyMdfReader/badge/?version=latest
        :alt: ReadTheDocs
        :target: https://pyMdfReader.readthedocs.io/en/stable/
    .. image:: https://img.shields.io/coveralls/github/<USER>/pyMdfReader/main.svg
        :alt: Coveralls
        :target: https://coveralls.io/r/<USER>/pyMdfReader
    .. image:: https://img.shields.io/pypi/v/pyMdfReader.svg
        :alt: PyPI-Server
        :target: https://pypi.org/project/pyMdfReader/
    .. image:: https://img.shields.io/conda/vn/conda-forge/pyMdfReader.svg
        :alt: Conda-Forge
        :target: https://anaconda.org/conda-forge/pyMdfReader
    .. image:: https://pepy.tech/badge/pyMdfReader/month
        :alt: Monthly Downloads
        :target: https://pepy.tech/project/pyMdfReader
    .. image:: https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter
        :alt: Twitter
        :target: https://twitter.com/pyMdfReader

.. image:: https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold
    :alt: Project generated with PyScaffold
    :target: https://pyscaffold.org/

|

===========
pyMdfReader
===========


A reader for Micro lab MDF files


Description
===========

This module is used to read the micro lab MDF data files. An efficient mechanism is used to allow to make
selection   of data columns.

Example of usage:
-----------------

Read a MDF file as a whole

.. code:: python

    import mdf_reader.mdf_parser as mdf
    data_file = "example_data_file.mdf"

    header_object = mdf.MDFParser(data_file)
    header_object.data.info()

Read a selection of columns based on a filter

.. code:: python

    header_object = mdf.MDFParser(data_file, import_data=False)
    header_object.set_column_selection(filter_list=["BALDER", "A[XYZ]"])
    header_object.import_data()

Note that the data is stored in a pandas data frame 'header_object.data'


Examples
========

A recipe to use the package can be found here.

* Loading and Plotting MDF files: :download:`html <../example/example_mdf_reader.html>`

Unit Test
=========
In order to run the standard unit test do::

    tox

Installation
============

To install the package run::

    pip install pyMdfReader

In case you want to run all the examples in a virtual environment you can also do::

    pip install pyMdfReader[examples]

which makes sure that a that also the package *matplotlib*, *seaborn* and *jupyter* are
installed as well.

Making Changes & Contributing
=============================

This project uses `pre-commit`_, please make sure to install it before making any
changes::

    pip install pre-commit
    cd pyMdfReader
    pre-commit install

It is a good idea to update the hooks to the latest version::

    pre-commit autoupdate

Don't forget to tell your contributors to also install and use pre-commit.

.. _pre-commit: https://pre-commit.com/

Note
====

This project has been set up using PyScaffold 4.5. For details and usage
information on PyScaffold see https://pyscaffold.org/.
