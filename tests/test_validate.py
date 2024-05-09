import os

import pytest
from importlib_resources import files
from yamale.yamale_error import YamaleError

from unity_initiator.actions import ACTION_MAP
from unity_initiator.utils.conf_utils import parse_router_file

# mock default region
os.environ["MOTO_ALLOW_NONEXISTENT_REGION"] = "True"
os.environ["AWS_DEFAULT_REGION"] = "hilo-hawaii-1"


def test_validate():
    """Test validation of router config for multiple use cases."""

    router_file = files("tests.resources").joinpath("test_router.yaml")
    assert isinstance(parse_router_file(router_file), dict)


def test_validate_bad_router_1():
    """Test validation of invalid router configuration: no payload_type specified."""

    router_file = files("tests.resources").joinpath("test_bad_router_1.yaml")
    with pytest.raises(
        YamaleError, match=r"initiator_config\.payload_type : 'None' is not a map"
    ):
        parse_router_file(router_file)


def test_validate_bad_router_2():
    """Test validation of invalid router configuration: no regexes specified."""

    router_file = files("tests.resources").joinpath("test_bad_router_2.yaml")
    with pytest.raises(YamaleError) as excinfo:
        parse_router_file(router_file)
    for error_str in (
        "initiator_config.payload_type.url.0.regexes: 'None' is not a list.",
        "initiator_config.payload_type.url.0.evaluators: Required field missing",
    ):
        assert error_str in str(excinfo.value)


def test_validate_bad_router_3():
    """Test validation of invalid router configuration: no evaluators specified."""

    router_file = files("tests.resources").joinpath("test_bad_router_3.yaml")
    with pytest.raises(
        YamaleError,
        match=r"initiator_config\.payload_type\.url\.0\.evaluators: 'None' is not a list",
    ):
        parse_router_file(router_file)


def test_validate_bad_router_4():
    """Test validation of invalid router configuration: unsupported action."""

    router_file = files("tests.resources").joinpath("test_bad_router_4.yaml")
    with pytest.raises(YamaleError) as excinfo:
        parse_router_file(router_file)
    for action in ACTION_MAP:
        assert (
            f"initiator_config.payload_type.url.0.evaluators.0.actions.0.name: some_unimplemented_action does not equal {action}"
            in str(excinfo.value)
        )


def test_validate_bad_router_5():
    """Test validation of invalid router configuration: no evaluators specified."""

    router_file = files("tests.resources").joinpath("test_bad_router_5.yaml")
    with pytest.raises(
        YamaleError,
        match=r"initiator_config\.payload_type\.url\.0\.evaluators\.0\.actions\.0\.params\.on_success\.actions\.0\.params: Required field missing",
    ):
        parse_router_file(router_file)


def test_validate_bad_router_6():
    """Test validation of invalid router configuration: dag_id required."""

    router_file = files("tests.resources").joinpath("test_bad_router_6.yaml")
    with pytest.raises(
        YamaleError,
        match=r"initiator_config\.payload_type\.url\.0\.evaluators\.0\.actions\.0\.params\.dag_id: Required field missing",
    ):
        parse_router_file(router_file)


def test_validate_bad_router_7():
    """Test validation of invalid router configuration: dag_id required on on_success action."""

    router_file = files("tests.resources").joinpath("test_bad_router_7.yaml")
    with pytest.raises(
        YamaleError,
        match=r"initiator_config\.payload_type\.url\.0\.evaluators\.0\.actions\.0\.params\.on_success\.actions\.0\.params\.dag_id: Required field missing",
    ):
        parse_router_file(router_file)
