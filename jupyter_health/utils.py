"""General utilties for jupyter_health"""

from __future__ import annotations

import base64
import json

import pandas as pd


def flatten_dict(d: dict | list, prefix: str = "") -> dict:
    """flatten a nested dictionary into

    adds nested keys to flat key names, so

    {
      "top": 1,
      "a": {"b": 5},
    }

    becomes

    {
      "top": 1,
      "a_b": 5,
    }
    """
    flat_dict = {}
    if isinstance(d, list):
        # treat list as dict with integer keys
        d = {i: item for i, item in enumerate(d)}
    for key, value in d.items():
        if prefix:
            key = f"{prefix}_{key}"

        if isinstance(value, (dict, list)):
            for sub_key, sub_value in flatten_dict(value, prefix=key).items():
                flat_dict[sub_key] = sub_value
        else:
            flat_dict[key] = value
    return flat_dict


def tidy_observation(observation: dict) -> dict:
    """Given a CHCS Observation, return a flat dictionary

    reshapes data to a one-level dictionary, appropriate for
    `pandas.from_records`.

    any fields ending with 'date_time' are parsed as timestamps
    """
    id = observation["id"]
    attachment = observation["valueAttachment"]
    if "json" not in attachment["contentType"]:
        raise ValueError(
            f"Unrecognized contentType={attachment['contentType']} in observation {id}"
        )

    record = json.loads(base64.b64decode(attachment["data"]))

    if "body" in record:
        record_header = record.get("header", {})
        record_body = record["body"]
    else:
        # older format, not sure we need to deal with this
        record_header = {}
        record_body = record
    # resolve code
    # todo: handle more than one?
    coding = observation["code"]["coding"][0]
    data = {
        "resource_type": coding["code"],
    }
    top_level_dict = {
        key: value
        for key, value in observation.items()
        if key not in {"valueAttachment"}
    }
    data.update(flatten_dict(top_level_dict))
    # currently assumes header and body namespaces have no collisions
    # this seems to be true, though. Alternately, could add `header_` to header
    data.update(flatten_dict(record_header))
    data.update(flatten_dict(record_body))
    for key in list(data):
        if key.endswith("date_time"):
            timestamp = data[key]
            # vega-lite doesn't like timestamps with tz info, so must be utc or naive
            # data[_date_time] is the utc timestamp
            data[key] = pd.to_datetime(timestamp, utc=True)
            # data[_date_time_local] is local time for the measurement (without tz info)
            # used for e.g. time-of-day binning
            data[key + "_local"] = pd.to_datetime(timestamp).tz_localize(None)
    return data
