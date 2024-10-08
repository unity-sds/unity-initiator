import asyncio
import json
import os

import boto3
import pytest
import respx
from httpx import Response
from importlib_resources import files
from moto import mock_aws
from yamale.yamale_error import YamaleError

from unity_initiator.actions import ACTION_MAP
from unity_initiator.evaluator import Evaluator
from unity_initiator.router import NoEvaluatorRegexMatched, Router
from unity_initiator.utils.logger import logger

# mock default region
os.environ["MOTO_ALLOW_NONEXISTENT_REGION"] = "True"
os.environ["AWS_DEFAULT_REGION"] = "hilo-hawaii-1"


@pytest.fixture(autouse=True)
def event_loop():
    """Create an instance of the default event loop for each test case."""

    policy = asyncio.get_event_loop_policy()
    res = policy.new_event_loop()
    asyncio.set_event_loop(res)
    res._close = res.close
    res.close = lambda: None
    yield res
    res._close()


def test_router_instantiation():
    """Test instantiation of router object for multiple use cases."""

    router_file = files("tests.resources").joinpath("test_router.yaml")
    router = Router(router_file)
    assert isinstance(router, Router)


def test_router_instantation_failure():
    """Test failure of creating a router object because of failed validation of router config."""

    router_file = files("tests.resources").joinpath("test_bad_router_1.yaml")
    with pytest.raises(
        YamaleError, match=r"initiator_config\.payload_type : 'None' is not a map"
    ):
        Router(router_file)


@mock_aws
def test_routing_sbg_url():
    """Test routing a url payload: SBG example"""

    url = "s3://bucket/prefix/SISTER_EMIT_L1B_RDN_20240103T131936_001/SISTER_EMIT_L1B_RDN_20240103T131936_001_OBS.bin"
    client = boto3.client("sns")
    router_file = files("tests.resources").joinpath("test_router.yaml")
    router = Router(router_file)
    evaluators = list(router.get_evaluators_by_url(url))
    assert len(evaluators) == 1
    for evaluator in evaluators:
        assert isinstance(evaluator, Evaluator)
        assert evaluator.name == "eval_sbg_l2_readiness"
        topic_arn = client.create_topic(
            Name=evaluator.name, Attributes={"TracingConfig": "Active"}
        )["TopicArn"]
        actions = list(evaluator.get_actions())
        assert len(actions) == 1
        for action in actions:
            assert isinstance(action, ACTION_MAP["submit_to_sns_topic"])
            assert action.topic_arn == topic_arn
            response = action.execute()
            assert response["success"]
            logger.info("response: %s", json.dumps(response, indent=2))


@mock_aws
def test_execute_actions_for_sbg_url():
    """Test routing a url payload and executing actions: SBG example"""

    url = "s3://bucket/prefix/SISTER_EMIT_L1B_RDN_20240103T131936_001/SISTER_EMIT_L1B_RDN_20240103T131936_001_OBS.bin"
    client = boto3.client("sns")
    router_file = files("tests.resources").joinpath("test_router.yaml")
    router = Router(router_file)
    client.create_topic(
        Name=list(router.get_evaluators_by_url(url))[0].name,
        Attributes={"TracingConfig": "Active"},
    )
    results = router.execute_actions(url)
    logger.info("results: %s", results)
    for res in results:
        assert res["success"]


@mock_aws
def test_execute_actions_for_m2020_url():
    """Test routing a url payload and executing actions: M2020 example"""

    client = boto3.client("sns")
    router_file = files("tests.resources").joinpath("test_router.yaml")
    router = Router(router_file)
    for test_file in (
        "ML01234567891011121_000RAS_N01234567890101112131415161.VIC-link",
        "MR01234567891011121_000RAS_N01234567890101112131415161.VIC-link",
        "ML01234567891011121_000DSP_N01234567890101112131415161.VIC-link",
    ):
        url = f"s3://bucket/ids-pipeline/pipes/nonlin_xyz_left/inputque/{test_file}"
        client.create_topic(
            Name=list(router.get_evaluators_by_url(url))[0].name,
            Attributes={"TracingConfig": "Active"},
        )
        results = router.execute_actions(url)
        logger.info("results: %s", results)
        for res in results:
            assert res["success"]


@mock_aws
def test_execute_actions_for_nisar_telemetry_url():
    """Test routing a url payload and executing actions: NISAR telemetry example"""

    url = "s3://bucket/prefix/NISAR_S198_PA_PA11_M00_P00922_R00_C01_G00_2024_010_17_57_57_714280000.vc29"
    client = boto3.client("sns")
    router_file = files("tests.resources").joinpath("test_router.yaml")
    router = Router(router_file)
    client.create_topic(
        Name=list(router.get_evaluators_by_url(url))[0].name,
        Attributes={"TracingConfig": "Active"},
    )
    results = router.execute_actions(url)
    logger.info("results: %s", results)
    for res in results:
        assert res["success"]


@respx.mock
@mock_aws
def test_execute_actions_for_nisar_ldf_url():
    """Test routing a url payload and executing actions: NISAR LDF example"""

    # mock airflow REST API
    respx.post("https://example.com/api/v1/dags/eval_nisar_l0a_readiness/dagRuns").mock(
        return_value=Response(
            200,
            json={
                "dag_run_id": "string",
                "dag_id": "eval_nisar_l0a_readiness",
                "logical_date": "2024-06-13T14:15:22Z",
                "execution_date": "2024-06-13T14:15:22Z",
                "start_date": "2024-06-13T14:15:22Z",
                "end_date": "2024-06-13T14:15:22Z",
                "data_interval_start": "2024-06-13T14:15:22Z",
                "data_interval_end": "2024-06-13T14:15:22Z",
                "last_scheduling_decision": "2024-06-13T14:15:22Z",
                "run_type": "dataset_triggered",
                "state": "queued",
                "external_trigger": True,
                "conf": {},
                "note": "",
            },
        )
    )

    url = "s3://bucket/prefix/NISAR_S198_PA_PA11_M00_P00922_R00_C01_G00_2024_010_18_03_05_087077000.ldf"
    client = boto3.client("sns")
    router_file = files("tests.resources").joinpath("test_router.yaml")
    router = Router(router_file)
    client.create_topic(
        Name=list(router.get_evaluators_by_url(url))[0].name,
        Attributes={"TracingConfig": "Active"},
    )
    results = router.execute_actions(url)
    logger.info("results: %s", results)
    for res in results:
        assert res["success"]


@respx.mock
@mock_aws
def test_execute_actions_for_airs_retstd_url():
    """Test routing a url payload and executing actions: AIRS RetStd example"""

    # mock mozart REST API
    respx.post("https://example.com/api/v0.1/job/submit").mock(
        return_value=Response(
            200,
            json={
                "success": True,
                "message": "",
                "result": "fda11fad-35f0-466e-a785-4678a0e662de",
                "tags": ["airs", "hysds"],
            },
        )
    )

    url = "s3://bucket/prefix/AIRS.2009.06.13.001.L2.RetStd.v6.0.7.0.G13077043030.hdf"
    client = boto3.client("sns")
    router_file = files("tests.resources").joinpath("test_router.yaml")
    router = Router(router_file)
    client.create_topic(
        Name=list(router.get_evaluators_by_url(url))[0].name,
        Attributes={"TracingConfig": "Active"},
    )
    results = router.execute_actions(url)
    logger.info("results: %s", results)
    for res in results:
        assert res["success"]


@mock_aws
def test_unrecognized_url():
    """Test routing a url payload that is unrecognized: NISAR L0B example"""

    url = "s3://bucket/prefix/NISAR_L0_PR_RRSD_063_136_A_129S_20240120T230041_20240120T230049_D00401_N_J_001.h5"
    router_file = files("tests.resources").joinpath("test_router.yaml")
    router = Router(router_file)
    with pytest.raises(NoEvaluatorRegexMatched, match=r"No regex matched url"):
        list(router.get_evaluators_by_url(url))
