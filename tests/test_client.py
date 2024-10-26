import os
from unittest import mock

from jupyter_health import JupyterHealthCHClient


def test_client_constructor():
    client = JupyterHealthCHClient(token="abc")
    assert client.session.headers == {"Authorization": "Bearer abc"}
    with mock.patch.dict(os.environ, {"CHCS_TOKEN": "xyz"}):
        client = JupyterHealthCHClient()
    assert client.session.headers == {"Authorization": "Bearer xyz"}


# TODO: really test the client, but we need mock responses first
