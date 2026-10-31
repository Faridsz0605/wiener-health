"""Store the Databricks PAT in the OS keyring (never in files or env)."""

from getpass import getpass

from _common import secrets

secrets.put("databricks_token", getpass("Databricks personal access token: "))
print("stored in keyring as wiener-data/databricks_token")
