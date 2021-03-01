"""Initialize the R dependencies.

The purpose of this module is to import all the R packages that are installed
into a sub-folder (see `config.R_LIBS_PATH`) in the project's root directory.

The Jupyter notebook "research/00_r_dependencies.ipynb" can be used to install all
R dependencies on a Ubuntu/Debian based system.
"""

from rpy2.rinterface_lib import callbacks as rcallbacks
from rpy2.robjects import packages as rpackages


# Suppress R's messages to stdout and stderr.
# Source: https://stackoverflow.com/a/63220287
rcallbacks.consolewrite_print = lambda msg: None  # pragma: no cover
rcallbacks.consolewrite_warnerror = lambda msg: None  # pragma: no cover


# For clarity and convenience, re-raise the error that results from missing R
# dependencies with clearer instructions as to how to deal with it.
try:  # noqa:WPS229
    rpackages.importr('forecast')
    rpackages.importr('zoo')

except rpackages.PackageNotInstalledError:  # pragma: no cover
    msg = 'See the "research/00_r_dependencies.ipynb" notebook!'
    raise rpackages.PackageNotInstalledError(msg) from None
