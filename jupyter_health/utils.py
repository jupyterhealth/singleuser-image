"""General utilties for jupyter_health"""

from __future__ import annotations

import pandas as pd
from commonhealth_cloud_storage_client import ResourceHolder


def flatten_dict(d: dict, prefix: str = "") -> dict:
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
    for key, value in d.items():
        if prefix:
            key = f"{prefix}_{key}"

        if isinstance(value, dict):
            for sub_key, sub_value in flatten_dict(value, prefix=key).items():
                flat_dict[sub_key] = sub_value
        else:
            flat_dict[key] = value
    return flat_dict


def tidy_record(record: ResourceHolder) -> dict:
    """Given a CHCS ResourceHolder, return a flat dictionary

    reshapes data to a one-level dictionary, appropriate for
    `pandas.from_records`.

    any fields ending with 'date_time' are parsed as timestamps
    """
    record_header = record.json_content["header"]
    record_body = record.json_content["body"]
    data = {
        "resource_type": record.resource_type,
    }
    # currently assumes header and body namespaces have no collisions
    # this seems to be true, though. Alternately, could add `header_` to header
    data.update(flatten_dict(record_header))
    data.update(flatten_dict(record_body))
    for key in data:
        if key.endswith("date_time"):
            data[key] = pd.to_datetime(data[key], utc=True)
    return data
