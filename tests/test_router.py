import asyncio
import json
import os

import boto3
import pytest
from importlib_resources import files
from moto import mock_aws
from yamale.yamale_error import YamaleError

from unity_initiator.actions import ACTION_MAP
from unity_initiator.evaluator import Evaluator
from unity_initiator.router import Router
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


def test_invalid_router_1():
    """Test failure of creating a router object because of failed validation of router config."""

    router_file = files("tests.resources").joinpath("test_bad_router_1.yaml")
    with pytest.raises(
        YamaleError, match=r"initiator_config\.payload_type : 'None' is not a map"
    ):
        Router(router_file)


@mock_aws
def test_route_url_1():
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
        topic_arn = client.create_topic(Name=evaluator.name)["TopicArn"]
        actions = list(evaluator.get_actions())
        assert len(actions) == 1
        for action in actions:
            assert isinstance(action, ACTION_MAP["submit_to_sns_topic"])
            assert action.topic_arn == topic_arn
            response = action.execute()
            assert response["success"]
            logger.info("response: %s", json.dumps(response, indent=2))


@mock_aws
def test_execute_actions_route_url_1():
    """Test routing a url payload and executing actions: SBG example"""

    url = "s3://bucket/prefix/SISTER_EMIT_L1B_RDN_20240103T131936_001/SISTER_EMIT_L1B_RDN_20240103T131936_001_OBS.bin"
    client = boto3.client("sns")
    router_file = files("tests.resources").joinpath("test_router.yaml")
    router = Router(router_file)
    client.create_topic(Name=list(router.get_evaluators_by_url(url))[0].name)
    results = router.execute_actions(url)
    logger.info("results: %s", results)
    for res in results:
        assert res["success"]


@mock_aws
def test_execute_actions_route_url_2():
    """Test routing a url payload and executing actions: M2020 example"""

    url = "s3://bucket/ids-pipeline/pipes/nonlin_xyz_left/inputque/ML01234567891011121_000RAS_N01234567890101112131415161.VIC-link"
    client = boto3.client("sns")
    router_file = files("tests.resources").joinpath("test_router.yaml")
    router = Router(router_file)
    client.create_topic(Name=list(router.get_evaluators_by_url(url))[0].name)
    results = router.execute_actions(url)
    logger.info("results: %s", results)
    for res in results:
        assert res["success"]
