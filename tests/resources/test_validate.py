from importlib_resources import files
from unity_initiator.utils.validate import validate_router


def test_validate():
    router_file = files("tests.resources").joinpath("test_router.yaml")
    assert validate_router(router_file) == True
