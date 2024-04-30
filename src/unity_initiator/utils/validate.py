import re
import logging
import yaml
import yamale

from yamale.validators import DefaultValidators, Validator
from importlib_resources import files


# set logger
log_format = "[%(asctime)s: %(levelname)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)
logger = logging.getLogger('unity_initiator.utils.validate')
logger.setLevel(logging.INFO)


# schema file
ROUTER_SCHEMA_FILE=files("unity_initiator.resources").joinpath("routers_schema.yaml")


# have yaml parse regular expressions
yaml.SafeLoader.add_constructor(
    "tag:yaml.org,2002:python/regexp",
    lambda lambd, n: re.compile(lambd.construct_scalar(n)),
)


class CompileRegex(Validator):
    tag = "compiled_regex"
    def _is_valid(self, value):
        return isinstance(value, re.Pattern)


def validate_router(router_file, schema_file=ROUTER_SCHEMA_FILE):
    validators = DefaultValidators.copy()
    validators[CompileRegex.tag] = CompileRegex
    try:
        schema = yamale.make_schema(schema_file, validators=validators)
        with open(router_file) as f:
            data = [(yaml.safe_load(f), router_file)]
        result = yamale.validate(schema, data)
    except yamale.YamaleError as e:
        logger.error(e.message)
        raise RuntimeError(e.message)
    return True
