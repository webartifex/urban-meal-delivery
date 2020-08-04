Urban Meal Delivery
===================

.. toctree::
   :hidden:
   :maxdepth: 1

   license
   reference


This is the documentation for the `urban-meal-delivery` package
that contains all the source code
used in a research project
residing in this `repository`_.


Prerequisites
-------------

Only `git`_, `Python`_ 3.8 and `poetry`_ must be available.
All other software is automatically installed (cf., next section).


Installation
------------

The `urban-meal-delivery` package is installed
only after cloning the `repository`_.
It is *not* available on `PyPI`_ via `pip`_.

.. code-block:: console

   $ git clone https://github.com/webartifex/urban-meal-delivery.git

Use `poetry`_ to install the package
with its dependencies into a `virtual environment`_,
which we also refer to as the **local** or the **develop** environment here.

.. code-block:: console

   $ poetry install


First Steps
-----------

Verify that the installation is in a good state by
running the test suite and the code linters
via the automated task runner `nox`_.

``poetry run`` executes whatever comes after it in the develop environment.
If you have a project-independent `nox`_ installation available,
you may drop the ``poetry run`` prefix.
Otherwise, `nox`_ was installed as a develop dependency in the `virtual environment`_
in the installation step above.

Run the default sessions in `nox`_:

.. code-block:: console

   $ [poetry run] nox

`nox`_ provides many options.
You can use them to choose among the different tasks you want to achieve.

.. option:: -l, --list

   List all available `nox`_ sessions.
   This includes sessions that are *not* run by default
   and that may be used as develop tools
   to work on the source files.

.. option:: -s [SESSION [SESSION ...]], --session[s] [SESSION [SESSION ...]]

   Run only the specified session[s]

.. option:: -r, --reuse-existing-virtualenvs

   By default,
   `nox`_ creates a new `virtual environment`_ for every session.
   To speed things up,
   one can re-use existing environments with the -r flag.
   This should only be done when developing
   and not before committing or on the CI server.


.. _git: https://git-scm.com/
.. _nox: https://nox.thea.codes/en/stable/
.. _pip: https://pip.pypa.io/en/stable/
.. _poetry: https://python-poetry.org/docs/
.. _pypi: https://pypi.org/
.. _python: https://docs.python.org/3/
.. _repository: https://github.com/webartifex/urban-meal-delivery
.. _virtual environment: https://docs.python.org/3/tutorial/venv.html
