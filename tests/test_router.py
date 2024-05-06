import pytest
from importlib_resources import files
from yamale.yamale_error import YamaleError

from unity_initiator.router import Router


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
