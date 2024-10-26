import pytest
from pandas import Timestamp

from jupyter_health.utils import flatten_dict, tidy_observation

# synthetic records matching real record structure
glucose_record = {
    "resourceType": "Observation",
    "id": "54321",
    "meta": {"lastUpdated": "2024-10-09T22:10:55.193492+00:00"},
    "status": "final",
    "subject": {"reference": "Patient/12345"},
    "code": {
        "coding": [
            {"code": "omh:blood-glucose:4.0", "system": "https://w3id.org/openmhealth"}
        ]
    },
    "valueAttachment": {
        "data": "eyJibG9vZF9nbHVjb3NlIjogeyJ1bml0IjogIm1nL2RMIiwgInZhbHVlIjogNjV9LCAic3BlY2ltZW5fc291cmNlIjogImNhcGlsbGFyeSBibG9vZCIsICJlZmZlY3RpdmVfdGltZV9mcmFtZSI6IHsidGltZV9pbnRlcnZhbCI6IHsiZW5kX2RhdGVfdGltZSI6ICIyMDI0LTAzLTA3VDA3OjI1OjAwWiIsICJzdGFydF9kYXRlX3RpbWUiOiAiMjAyNC0wMy0wN1QwNzoyNTowMFoifX0sICJkZXNjcmlwdGl2ZV9zdGF0aXN0aWMiOiAibWluaW11bSIsICJ0ZW1wb3JhbF9yZWxhdGlvbnNoaXBfdG9fbWVhbCI6ICJmYXN0aW5nIiwgInRlbXBvcmFsX3JlbGF0aW9uc2hpcF90b19zbGVlcCI6ICJvbiB3YWtpbmcifQ==",
        "contentType": "application/json",
    },
}

tidy_glucose_record = {
    "blood_glucose_unit": "mg/dL",
    "blood_glucose_value": 65,
    "code_coding_0_code": "omh:blood-glucose:4.0",
    "code_coding_0_system": "https://w3id.org/openmhealth",
    "descriptive_statistic": "minimum",
    "effective_time_frame_time_interval_end_date_time": Timestamp(
        "2024-03-07 07:25:00+0000", tz="UTC"
    ),
    "effective_time_frame_time_interval_end_date_time_local": Timestamp(
        "2024-03-07 07:25:00"
    ),
    "effective_time_frame_time_interval_start_date_time": Timestamp(
        "2024-03-07 07:25:00+0000", tz="UTC"
    ),
    "effective_time_frame_time_interval_start_date_time_local": Timestamp(
        "2024-03-07 07:25:00"
    ),
    "id": "54321",
    "meta_lastUpdated": "2024-10-09T22:10:55.193492+00:00",
    "resourceType": "Observation",
    "resource_type": "omh:blood-glucose:4.0",
    "specimen_source": "capillary blood",
    "status": "final",
    "subject_reference": "Patient/12345",
    "temporal_relationship_to_meal": "fasting",
    "temporal_relationship_to_sleep": "on waking",
}

bp_record = {
    "resourceType": "Observation",
    "id": "54322",
    "meta": {"lastUpdated": "2024-10-09T17:04:36.617988+00:00"},
    "status": "final",
    "subject": {"reference": "Patient/12345"},
    "code": {
        "coding": [
            {"code": "omh:blood-pressure:4.0", "system": "https://w3id.org/openmhealth"}
        ]
    },
    "valueAttachment": {
        "data": "eyJlZmZlY3RpdmVfdGltZV9mcmFtZSI6IHsiZGF0ZV90aW1lIjogIjIwMjQtMDQtMTBUMDg6MzY6MDAtMDE6MDAifSwgInN5c3RvbGljX2Jsb29kX3ByZXNzdXJlIjogeyJ1bml0IjogIm1tSGciLCAidmFsdWUiOiAxMjB9LCAiZGlhc3RvbGljX2Jsb29kX3ByZXNzdXJlIjogeyJ1bml0IjogIm1tSGciLCAidmFsdWUiOiA4MH19",
        "contentType": "application/json",
    },
}

tidy_bp_record = {
    "code_coding_0_code": "omh:blood-pressure:4.0",
    "code_coding_0_system": "https://w3id.org/openmhealth",
    "diastolic_blood_pressure_unit": "mmHg",
    "diastolic_blood_pressure_value": 80,
    "effective_time_frame_date_time": Timestamp("2024-04-10 09:36:00+0000", tz="UTC"),
    "effective_time_frame_date_time_local": Timestamp("2024-04-10 08:36:00"),
    "id": "54322",
    "meta_lastUpdated": "2024-10-09T17:04:36.617988+00:00",
    "resourceType": "Observation",
    "resource_type": "omh:blood-pressure:4.0",
    "status": "final",
    "subject_reference": "Patient/12345",
    "systolic_blood_pressure_unit": "mmHg",
    "systolic_blood_pressure_value": 120,
}


@pytest.mark.parametrize(
    "in_d, expected",
    [
        pytest.param({}, {}, id="empty"),
        pytest.param({"a": 5}, {"a": 5}, id="simple"),
        pytest.param({"a": ["x", "y"]}, {"a_0": "x", "a_1": "y"}, id="list"),
        pytest.param({"a": {"x": 5}, "b": 10}, {"a_x": 5, "b": 10}, id="nest"),
    ],
)
def test_flatten_dict(in_d, expected):
    assert flatten_dict(in_d) == expected


@pytest.mark.parametrize(
    "observation, tidy",
    [
        pytest.param(bp_record, tidy_bp_record, id="bp"),
        pytest.param(glucose_record, tidy_glucose_record, id="glucose"),
    ],
)
def test_tidy_observation(observation, tidy):
    assert tidy_observation(observation) == tidy
