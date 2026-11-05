import keyring
from keyring.backend import KeyringBackend

from core import secrets


class MemoryKeyring(KeyringBackend):
    priority = 1

    def __init__(self):
        self.store = {}

    def get_password(self, service, username):
        return self.store.get((service, username))

    def set_password(self, service, username, password):
        self.store[(service, username)] = password

    def delete_password(self, service, username):
        del self.store[(service, username)]


def test_secrets_use_project_service():
    backend = MemoryKeyring()
    previous = keyring.get_keyring()
    keyring.set_keyring(backend)
    try:
        secrets.put("databricks_token", "synthetic-token")
        assert backend.store == {("wiener-data", "databricks_token"): "synthetic-token"}
        assert secrets.get("databricks_token") == "synthetic-token"
        secrets.delete("databricks_token")
        assert secrets.get("databricks_token") is None
    finally:
        keyring.set_keyring(previous)
