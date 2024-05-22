import json
import os
from importlib.metadata import version
from uuid import uuid4

import boto3
import docker
import pytest
import respx
from botocore.exceptions import ClientError
from httpx import Response
from importlib_resources import files
from moto import mock_aws

from unity_initiator.cloud.lambda_handler import lambda_handler_base
from unity_initiator.utils.logger import logger

# mock default region
os.environ["MOTO_ALLOW_NONEXISTENT_REGION"] = "True"
os.environ["AWS_DEFAULT_REGION"] = "hilo-hawaii-1"


@respx.mock
@mock_aws
def lambda_handler(event, context):
    """Lambda handler that mocks AWS and Airflow API calls."""

    # create mock SNS topics
    client = boto3.client("sns")
    client.create_topic(Name="eval_sbg_l2_readiness")["TopicArn"]
    client.create_topic(Name="eval_m2020_xyz_left_finder")["TopicArn"]
    client.create_topic(Name="eval_nisar_ingest")["TopicArn"]

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

    return lambda_handler_base(event, context)


def get_role_name():
    """Get mock role ARN."""

    with mock_aws():
        iam = boto3.client("iam")
        while True:
            try:
                return iam.get_role(RoleName="my-role")["Role"]["Arn"]
            except ClientError:
                try:
                    return iam.create_role(
                        RoleName="my-role",
                        AssumeRolePolicyDocument="some policy",
                        Path="/my-path/",
                    )["Role"]["Arn"]
                except ClientError:
                    pass


@pytest.fixture(scope="module", autouse=True)
def build_mock_lambda_package():
    """Build the mock lambda package."""

    build_lambda_script = files("scripts").joinpath("build_mock_lambda_package.sh")
    logger.info(
        "Running build_lambda_script: %s\nThis may take some time...",
        build_lambda_script,
    )
    client = docker.from_env()
    client.containers.run(
        "mlupin/docker-lambda:python3.9-build",
        "./scripts/build_mock_lambda_package.sh",
        auto_remove=True,
        volumes={
            f"{os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))}": {
                "bind": "/var/task",
                "mode": "rw",
            }
        },
    )


def get_lambda_code():
    """Get lambda package zip as byte string."""

    zip_file = files("dist").joinpath(
        f"unity_initiator-{version('unity_initiator')}-mock_lambda.zip"
    )
    with open(zip_file, "rb") as f:
        return f.read()


class TestLambdaInvocations:
    mock = mock_aws()

    @classmethod
    def setup_class(cls):
        cls.mock.start()
        cls.client = boto3.client("lambda")
        cls.function_name = str(uuid4())[0:6]

        # TODO: Should use either AppConfig or retrieve router config from S3 location.
        # For now, writing out router config body to env variable to pass to lambda.
        cls.router_file = files("tests.resources").joinpath("test_router.yaml")
        with open(cls.router_file) as f:
            cls.router_cfg = f.read()

        cls.fxn = cls.client.create_function(
            FunctionName=cls.function_name,
            Runtime="python3.11",
            Role=get_role_name(),
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": get_lambda_code()},
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            Publish=True,
            Environment={"Variables": {"ROUTER_CFG": cls.router_cfg}},
        )

    @classmethod
    def teardown_class(cls):
        try:
            cls.mock.stop()
        except RuntimeError:
            pass

    def test_invoke_function_all_test_cases(self):
        """Test invocations of the router lambda using all current test cases: SBG, M2020 and NISAR."""

        # SBG use case
        in_data = {
            "payload": "s3://bucket/prefix/SISTER_EMIT_L1B_RDN_20240103T131936_001/SISTER_EMIT_L1B_RDN_20240103T131936_001_OBS.bin"
        }
        invoke_res = self.client.invoke(
            FunctionName=self.function_name,
            InvocationType="Event",
            Payload=json.dumps(in_data),
        )
        logger.info("invoke_res: %s", invoke_res)
        results = json.loads(invoke_res["Payload"].read().decode("utf-8"))
        logger.info("results: %s", results)
        for res in results:
            assert res["success"]

        # M2020 use case
        for test_file in (
            "ML01234567891011121_000RAS_N01234567890101112131415161.VIC-link",
            "MR01234567891011121_000RAS_N01234567890101112131415161.VIC-link",
            "ML01234567891011121_000DSP_N01234567890101112131415161.VIC-link",
        ):
            url = f"s3://bucket/ids-pipeline/pipes/nonlin_xyz_left/inputque/{test_file}"
            in_data = {"payload": url}
            invoke_res = self.client.invoke(
                FunctionName=self.function_name,
                InvocationType="Event",
                Payload=json.dumps(in_data),
            )
            logger.info("invoke_res: %s", invoke_res)
            results = json.loads(invoke_res["Payload"].read().decode("utf-8"))
            logger.info("results: %s", results)
            for res in results:
                assert res["success"]

        # NISAR telemetry use case
        in_data = {
            "payload": "s3://bucket/prefix/NISAR_S198_PA_PA11_M00_P00922_R00_C01_G00_2024_010_17_57_57_714280000.vc29"
        }
        invoke_res = self.client.invoke(
            FunctionName=self.function_name,
            InvocationType="Event",
            Payload=json.dumps(in_data),
        )
        logger.info("invoke_res: %s", invoke_res)
        results = json.loads(invoke_res["Payload"].read().decode("utf-8"))
        logger.info("results: %s", results)
        for res in results:
            assert res["success"]

        # NISAR LDF use case
        in_data = {
            "payload": "s3://bucket/prefix/NISAR_S198_PA_PA11_M00_P00922_R00_C01_G00_2024_010_18_03_05_087077000.ldf"
        }
        invoke_res = self.client.invoke(
            FunctionName=self.function_name,
            InvocationType="Event",
            Payload=json.dumps(in_data),
        )
        logger.info("invoke_res: %s", invoke_res)
        results = json.loads(invoke_res["Payload"].read().decode("utf-8"))
        logger.info("results: %s", results)
        for res in results:
            assert res["success"]

    def test_invoke_function_unrecognized(self):
        """Test invocations of the router lambda using an unrecognized url."""

        in_data = {
            "payload": "s3://bucket/prefix/NISAR_L0_PR_RRSD_063_136_A_129S_20240120T230041_20240120T230049_D00401_N_J_001.h5"
        }
        invoke_res = self.client.invoke(
            FunctionName=self.function_name,
            InvocationType="Event",
            Payload=json.dumps(in_data),
        )
        logger.info("invoke_res: %s", invoke_res)
        results = json.loads(invoke_res["Payload"].read().decode("utf-8"))
        logger.info("results: %s", results)
        assert results["errorType"] == "NoEvaluatorRegexMatched"
