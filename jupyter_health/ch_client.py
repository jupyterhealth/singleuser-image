"""JupyterHealth subclass of CommonHealth client

- sets default values
- loads state from AWS Secrets (credentials loaded by default)
"""

from __future__ import annotations

import json
from collections.abc import ItemsView, KeysView

import boto3.session
import pandas as pd
from commonhealth_cloud_storage_client import CHClient, CHStorageDelegate

from .utils import tidy_record


# TODO: Move these classes to separate storage delegate class
class AWSSecretStorageDelegate(CHStorageDelegate):
    """Implement CommonHealth storage delegate API backed by AWS secret"""

    def __init__(
        self, secret_name: str, *, client: boto3.session.Session | None = None
    ):
        """Construct a CHStorageDelegate backed by an AWS Secret

        Args:
            secret_name: the name of the secret
            client (optional): the boto3 secretsmanager client
                If not defined, will be constructed with defaults from the environment
        """
        if client is None:
            session = boto3.session.Session()
            self.client = session.client("secretsmanager")
        self.client = client
        self.secret_name = secret_name
        self._cached_value = None

    def _load(self):
        """Load the secret value into a local cache"""
        secret_response = self.client.get_secret_value(SecretId=self.secret_name)
        self._cached_value = json.loads(secret_response["SecretString"])

    def _save(self):
        """Persist any changes to the secret"""
        self.client.update_secret(
            SecretId=self.secret_name,
            SecretString=json.dumps(self._cached_value),
        )

    @property
    def _secret_value(self):
        """The value of the secret as a dict

        Loads it if it hasn't been loaded yet
        """
        if self._cached_value is None:
            self._load()
        return self._cached_value

    # the storage delegate API

    def get_secure_value(self, key: str, default=None) -> str | None:
        """Retrieve one secret value

        if not defined, return None
        """
        return self._secret_value.get(key, default)

    def set_secure_value(self, key: str, value: str) -> None:
        """Set one new value"""
        # load before writing to avoid writing back stale state
        self._load()
        self._secret_value[key] = value
        self._save()

    def clear_value(self, key: str) -> None:
        """Remove one value from the storage"""
        if key not in self._secret_value:
            return
        self._secret_value.pop(key)
        self._save()

    def clear_all_values(self) -> None:
        """Clear all values in the storage

        Probably shouldn't do this!
        """
        raise NotImplementedError("clear all values not allowed")
        self._load()
        new_value = {}
        # don't allow deleting signing key
        if "private_signing_key" in self._cached_value:
            new_value["private_signing_key"] = self._cached_value["private_signing_key"]
        self._cached_value = new_value
        self._save()

    # additional API methods not in the base class

    def keys(self) -> KeysView:
        """Return currently stored keys, like dict.keys()"""
        return self._secret_value.keys()

    def items(self) -> ItemsView:
        """Return currently stored items, like `dict.items()`"""
        return self._secret_value.items()


class JupyterHealthCHClient(CHClient):
    """JupyterHealth client for CommonHealth Cloud

    Fills out default values for all args and loads state from AWS Secrets
    """

    def __init__(self, deployment: str = "prod", *, client=None, **user_kwargs):
        """Construct a JupyterHealth cilent for Common Health Cloud

        Credentials will be loaded from the environment and defaults.
        No arguments are required.

        By default, creates a client connected to the 'prod' pre-MVP application,
        but pass::

            JupyterHealthCHClient("testing")

        to connect to the testing application.

        A boto3 `client=Session().client("secretsmanager")` can be provided,
        otherwise a default client will be constructed loading credentials from the environment
        (works on the JupyterHealth deployment).

        Any additional keyword arguments will be passed through to CHClient
        """
        self.deployment = deployment

        # the names of the secrets where state is stored:
        storage_delegate_secret_name = f"ch-cloud-delegate-{deployment}"
        credentials_secret_name = f"ch-cloud-creds-{deployment}"

        # connect the client
        if client is None:
            session = boto3.session.Session()
            client = session.client(
                service_name="secretsmanager", region_name="us-east-2"
            )
            # Fails without missing region name
        self.client = client

        # fetch client_id/secret for the ch cloud API
        credentials_secret = self.client.get_secret_value(
            SecretId=credentials_secret_name
        )
        credentials = json.loads(credentials_secret["SecretString"])

        # construct storage delegate backed by AWS Secret
        storage = AWSSecretStorageDelegate(
            client=self.client, secret_name=storage_delegate_secret_name
        )
        # fill out default kwargs for the base class constructor
        kwargs = dict(
            ch_authorization_deeplink="https://appdev.tcpdev.org/m/phr/cloud-sharing/authorize",
            ch_host="chcs.tcpdev.org",
            ch_port=443,
            ch_scheme="https",
            storage_delegate=storage,
            partner_id=credentials["partner_id"],
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"],
        )
        # load user_kwargs so they can override any of the defaults above
        kwargs.update(user_kwargs)
        super().__init__(**kwargs)

    # additional API

    def list_patients(self) -> list[str]:
        """Return list of patient ids

        These are the keys that may be passed to e.g. fetch_data
        """
        patient_list = []
        for key in self.storage_delegate.keys():
            if key.startswith("patient_id_mapping/"):
                _prefix, _, name = key.partition("/")
                patient_list.append(name)
        return patient_list

    def fetch_data_frame(self, patient_id: str) -> pd.DataFrame:
        """Wrapper around fetch_data, returns a DataFrame"""
        resources = self.fetch_data(patient_id)
        records = [tidy_record(r) for r in resources]
        return pd.DataFrame.from_records(records)
