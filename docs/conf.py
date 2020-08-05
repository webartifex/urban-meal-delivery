"""Configure sphinx."""

import urban_meal_delivery as umd


project = umd.__pkg_name__
author = umd.__author__
copyright = f'2020, {author}'  # pylint:disable=redefined-builtin
version = release = umd.__version__

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
]
