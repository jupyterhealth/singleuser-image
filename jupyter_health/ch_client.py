"""JupyterHealth client implementation

wraps Exchange and FHIR APIs in convenience methods
"""

from __future__ import annotations

import os
import warnings
from enum import Enum
from typing import Any, Generator, Literal, cast, overload

import pandas as pd
import requests
from yarl import URL

from .utils import tidy_observation

_EXCHANGE_URL = os.environ.get("JHE_URL", "https://jhe.fly.dev")


class Code(Enum):
    """Enum of recognized coding values"""

    BLOOD_PRESSURE = "omh:blood-pressure:4.0"
    BLOOD_GLUCOSE = "omh:blood-glucose:4.0"


class RequestError(requests.HTTPError):
    """Subclass of request error that shows the actual error"""

    def __init__(self, requests_error: requests.HTTPError) -> None:
        """Wrap a requests HTTPError"""
        self.requests_error = requests_error

    def __str__(self) -> str:
        """Add the actual error, not just the generic HTTP status code"""
        response = self.requests_error.response
        chunks = [str(self.requests_error)]
        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type:
            detail = "(html error page)"
        else:
            try:
                # extract detail from JSON
                detail = response.json()["detail"]
            except Exception:
                # truncate so it doesn't get too long
                try:
                    detail = response.text[:1024]
                except Exception:
                    # encoding error?
                    detail = None
        if detail:
            chunks.append(detail)
        return "\n".join(chunks)


class JupyterHealthClient:
    """
    Client for JupyterHealth data Exchange
    """

    def __init__(self, url: str = _EXCHANGE_URL, *, token: str | None = None):
        """Construct a client for JupyterHealth  data exchange

        Credentials will be loaded from the environment and defaults.
        No arguments are required.

        By default, creates a client connected to the MVP application.
        """
        if token is None:
            token = os.environ.get("JHE_TOKEN", None)
            if token is None:
                token = os.environ.get("CHCS_TOKEN", None)
                warnings.warn(
                    "$CHCS_TOKEN env is deprecated, use $JHE_TOKEN",
                    DeprecationWarning,
                    stacklevel=2,
                )

        self._url = URL(url)
        self.session = requests.Session()
        self.session.headers = {"Authorization": f"Bearer {token}"}

    @overload
    def _api_request(
        self, path: str, *, return_response: Literal[True], **kwargs
    ) -> requests.Response: ...

    @overload
    def _api_request(
        self, path: str, *, method: str = "GET", check=True, fhir=False, **kwargs
    ) -> dict[str, Any] | None: ...

    def _api_request(
        self,
        path: str,
        *,
        method: str = "GET",
        check=True,
        return_response=False,
        fhir=False,
        **kwargs,
    ) -> dict[str, Any] | requests.Response | None:
        """Make an API request"""
        if fhir:
            url = self._url / "fhir/r5"
        else:
            url = self._url / "api/v1"
        url = url / path
        r = self.session.request(method, str(url), **kwargs)
        if check:
            try:
                r.raise_for_status()
            except requests.HTTPError as e:
                raise RequestError(e) from None
        if return_response:
            return r
        if r.content:
            return r.json()
        else:
            # return None for empty response body
            return None

    def _list_api_request(self, path: str, **kwargs) -> Generator[dict[str, Any]]:
        """Get a list from an /api/v1 endpoint"""
        r: dict = self._api_request(path, **kwargs)
        yield from r["results"]
        # TODO: handle pagination fields

    def _fhir_list_api_request(self, path: str, **kwargs) -> Generator[dict[str, Any]]:
        """Get a list from a fhir endpoint"""
        r: dict = self._api_request(path, fhir=True, **kwargs)
        for entry in r["entry"]:
            # entry seems to always be a dict with one key?
            if isinstance(entry, dict) and len(entry) == 1:
                # return entry['resource'] which is ~always the only thing
                # in the list
                yield list(entry.values())[0]
            else:
                yield entry
        # TODO: handle pagination fields

    def get_user(self) -> dict[str, Any]:
        """Get the current user"""
        return cast(dict[str, Any], self._api_request("users/profile"))

    def get_patient(self, id: int) -> dict[str, Any]:
        """Get a single patient by id"""
        return cast(dict[str, Any], self._api_request(f"patients/{id}"))

    def list_patients(self) -> Generator[dict[str, dict[str, Any]]]:
        """Return iterator of patients

        Patient ids are the keys that may be passed to e.g. fetch_data
        """
        return self._list_api_request("patients")

    def get_patient_consents(self, patient_id: int) -> dict[str, Any]:
        """Return patient consent status"""
        return cast(
            dict[str, Any], self._api_request(f"patients/{patient_id}/consents")
        )

    def get_study(self, id: int) -> dict[str, Any]:
        """Get a single study by id"""
        return cast(dict[str, Any], self._api_request(f"studies/{id}"))

    def list_studies(self) -> Generator[dict[str, dict[str, Any]]]:
        """Return iterator of studies

        Only returns studies I have access to (i.e. owned by my organization(s))
        """
        return self._list_api_request("studies")

    def get_organization(self, id: int) -> dict[str, Any]:
        """Get a single organization by id"""
        return cast(dict[str, Any], self._api_request(f"organizations/{id}"))

    def list_organizations(self) -> Generator[dict[str, dict[str, Any]]]:
        """Return iterator of all organizations

        Includes all organizations, including those of which I am not a member.
        The ROOT organization has `id=0`.
        """
        return self._list_api_request("organizations")

    def list_observations(
        self,
        patient_id: str | None = None,
        study_id: str | None = None,
        code: str | None = None,
    ) -> Generator[dict]:
        """Fetch observations for given patient and/or study

        At least one of patient_id and study_id is required.

        code is optional, and can be selected from enum JupyterHealth.Code
        """
        if not patient_id and not study_id:
            raise ValueError("Must specify at least one of patient_id or study_id")
        params = {}
        if study_id:
            params["_has:Group:member:_id"] = study_id
        if patient_id:
            params["patient"] = patient_id
        if code:
            if isinstance(code, Code):
                code = code.value
            if code is None or "|" not in code:
                # no code system specified, default to openmhealth
                code = f"https://w3id.org/openmhealth|{code}"
            params["code"] = code
        return self._fhir_list_api_request("Observation", params=params)

    def list_observations_df(
        self,
        patient_id: str | None = None,
        study_id: str | None = None,
        code: str | None = None,
    ) -> pd.DataFrame:
        """Wrapper around list_observations, returns a DataFrame"""
        observations = self.list_observations(
            patient_id=patient_id, study_id=study_id, code=code
        )
        records = [tidy_observation(obs) for obs in observations]
        return pd.DataFrame.from_records(records)


class JupyterHealthCHClient(JupyterHealthClient):
    """Deprecated name for JupyterHealthClient"""

    def __init__(self, *args, **kwargs):
        """construct Jupyter"""
        warnings.warn(
            "JupyterHealthCHClient is deprecated. Use JupyterHealthClient",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
