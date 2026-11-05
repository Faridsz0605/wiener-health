from collections.abc import Iterator

from databricks.sdk.errors import NotFound
from databricks.sdk.mixins.files import FilesExt
from databricks.sdk.service.files import DirectoryEntry


def _entries(files: FilesExt, path: str) -> Iterator[DirectoryEntry]:
    """Children before their parent directory, so entries can be deleted in order."""
    for entry in files.list_directory_contents(path):
        if entry.is_directory:
            yield from _entries(files, entry.path)
        yield entry


def count_objects(files: FilesExt, path: str) -> int:
    try:
        return sum(1 for _ in _entries(files, path))
    except NotFound:
        return 0


def remove_tree(files: FilesExt, path: str) -> None:
    try:
        entries = list(_entries(files, path))
    except NotFound:
        return
    for entry in entries:
        if entry.is_directory:
            files.delete_directory(entry.path)
        else:
            files.delete(entry.path)
    files.delete_directory(path)
