import io
from types import SimpleNamespace

from databricks.sdk.errors import NotFound
from databricks.sdk.service.files import DirectoryEntry


class FakeFiles:
    """In-memory stand-in for the Databricks Files API (volume paths)."""

    def __init__(self):
        self.objects = {}

    def upload(self, path, contents, *, overwrite=False):
        if path in self.objects and not overwrite:
            raise FileExistsError(path)
        self.objects[path] = contents.read()

    def download(self, path):
        return SimpleNamespace(contents=io.BytesIO(self.objects[path]))

    def _children(self, path):
        prefix = path.rstrip("/") + "/"
        names = {p[len(prefix) :].split("/")[0] for p in self.objects if p.startswith(prefix)}
        return sorted(names), prefix

    def list_directory_contents(self, path):
        names, prefix = self._children(path)
        if not names:
            raise NotFound(path)
        for name in names:
            full = prefix + name
            yield DirectoryEntry(path=full, is_directory=full not in self.objects)

    def delete(self, path):
        del self.objects[path]

    def delete_directory(self, path):
        if self._children(path)[0]:
            msg = f"directory not empty: {path}"
            raise OSError(msg)
