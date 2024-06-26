"""JupyterHealth subclass of CommonHealth client

- sets default values
- loads state from postgresql database
"""

from __future__ import annotations

import json
import logging
import time

import boto3
import pandas as pd
from commonhealth_cloud_storage_client import CHClient, CHStorageDelegate
from commonhealth_cloud_storage_client.errors import ImproperlyConfigured
from psycopg2 import InterfaceError, OperationalError, connect

from .utils import tidy_record


class PSQLStorageDelegate(CHStorageDelegate):
    """Implement CommonHealth storage delegate API backed by managed encrypted PostgreSQL database"""

    table_create = """CREATE TABLE IF NOT EXISTS key_value 
    (key TEXT NOT NULL, enc_value TEXT NOT NULL, date INTEGER NOT NULL, CONSTRAINT unique_key UNIQUE (key));"""

    insert = """INSERT INTO key_value (key, enc_value, date) 
    VALUES (%s, %s, %s) 
    ON CONFLICT (key) DO UPDATE SET 
    enc_value=EXCLUDED.enc_value,
    date=EXCLUDED.date"""

    def __init__(
        self,
        host: str,
        password: str,
        dbname: str = "postgres",
        user="postgres",
        port=5432,
        **kwargs,
    ):
        """Construct a CHStorageDelegate backed by a Postgres database

        Args:
            host: the location of the database
            password: the password or access token to the database
            dbname (optional): the database name, defaults to "postgres"
            user (optional): the database user name, defaults to "postgres"
            port (optional): the exposed port, defaults to 5432
        """
        self.logger = kwargs.get("logger", logging.getLogger(__name__))
        self.logger.info(f"Connecting to {host}")
        sslmode = kwargs.pop("sslmode", "require")
        try:
            self.conn = connect(
                dbname=dbname,
                user=user,
                host=host,
                password=password,
                port=port,
                sslmode=sslmode,
            )
        except (OperationalError, InterfaceError) as e:
            self.logger.warning(f"Error connecting to the database: {e}")
            raise ImproperlyConfigured from e

        self.logger.info("Connection established")
        self._init()

    def _init(self):
        with self.conn.cursor() as cursor:
            cursor.execute(PSQLStorageDelegate.table_create)

    def get_secure_value(self, key: str) -> str | None:
        """Load the secret value from the database"""
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM key_value WHERE key=%s LIMIT 1", (key,))
            row = cursor.fetchone()
            if not row:
                logging.warning(f"No data found for {key}")
                return None
            self.logger.debug(f"Retrieved row {row}")
            return row[1]

    def set_secure_value(self, key: str, value: str) -> None:
        """Set a secret value in the database"""
        self.logger.debug(f"Setting secure value for {key}")
        with self.conn.cursor() as cursor:
            cursor.execute(PSQLStorageDelegate.insert, (key, value, time.time()))
        self.logger.debug(f"Data inserted for {key}")

    def clear_value(self, key) -> None:
        """Remove a value from the database"""
        with self.conn.cursor() as cursor:
            cursor.execute("DELETE FROM key_value WHERE key=%s", (key,))
        self.logger.debug(f"Data removed for {key}")

    def clear_all_values(self) -> None:
        """Remove all values from the database"""
        with self.conn.cursor() as cursor:
            cursor.execute("DELETE FROM key_value")
        self.logger.debug("All values cleared")


class JupyterHealthCHClient(CHClient):
    """JupyterHealth client for CommonHealth Cloud

    Fills out default values for all args and loads state from AWS Secrets
    """

    def __init__(
        self, host, password, deployment: str = "prod", *, client=None, **user_kwargs
    ):
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
        credentials_secret_name = f"ch-cloud-creds-{deployment}"

        # connect the client
        if client is None:
            session = boto3.session.Session()
            client = session.client("secretsmanager")
        self.client = client

        # fetch client_id/secret for the ch cloud API
        credentials_secret = self.client.get_secret_value(
            SecretId=credentials_secret_name
        )
        credentials = json.loads(credentials_secret["SecretString"])

        # construct storage delegate backed by AWS Secret
        storage = PSQLStorageDelegate(host=host, password=password)
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
