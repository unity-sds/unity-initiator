import re

import yamale
import yaml
from importlib_resources import files
from yamale.validators import DefaultValidators, Validator

from .logger import logger

# schema file
ROUTER_SCHEMA_FILE = files("unity_initiator.resources").joinpath("routers_schema.yaml")


# have yaml parse regular expressions
yaml.SafeLoader.add_constructor(
    "tag:yaml.org,2002:python/regexp",
    lambda lambd, n: re.compile(lambd.construct_scalar(n)),
)


class CompileRegex(Validator):
    tag = "compiled_regex"

    def _is_valid(self, value):
        return isinstance(value, re.Pattern)


def parse_router_file(router_file, schema_file=ROUTER_SCHEMA_FILE):
    validators = DefaultValidators.copy()
    validators[CompileRegex.tag] = CompileRegex
    try:
        schema = yamale.make_schema(schema_file, validators=validators)
        with open(router_file, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        data = [(cfg, router_file)]
        yamale.validate(schema, data)
        return cfg
    except yamale.YamaleError as e:
        logger.error(e.message)
        raise
