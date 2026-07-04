"""Package resource helpers."""

from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path


def package_resource(name):
    """Return a traversable package resource."""
    parts = name.split("/")
    try:
        return files("fdlogger").joinpath(*parts)
    except ModuleNotFoundError:
        return Path(__file__).resolve().parents[1].joinpath(*parts)


@contextmanager
def resource_path(name):
    """Yield a filesystem path for a package resource file."""
    with as_file(package_resource(name)) as path:
        yield str(path)


def open_resource(name, mode="r", encoding=None):
    """Open a package resource."""
    return package_resource(name).open(mode, encoding=encoding)
