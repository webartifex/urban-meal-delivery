"""Configure sphinx."""

import velofy


project = velofy.__pkg_name__
author = velofy.__author__
copyright = f'2020, {author}'
version = release = velofy.__version__

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
]
