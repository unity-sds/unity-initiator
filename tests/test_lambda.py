import json
import os
import time
from importlib.metadata import version
from uuid import uuid4

import boto3
import docker
import pytest
import respx
import smart_open
from botocore.exceptions import ClientError
from httpx import Response
from importlib_resources import files
from moto import mock_aws

from unity_initiator.cloud.lambda_handler import (
    lambda_handler_base,
    lambda_handler_initiator,
)
from unity_initiator.utils.logger import logger

# mock default region
os.environ["MOTO_ALLOW_NONEXISTENT_REGION"] = "True"
os.environ["AWS_DEFAULT_REGION"] = "hilo-hawaii-1"


# test bucket for mock
TEST_BUCKET = "test_bucket"


def setup_mock_resources():
    """Create mocked AWS and Airflow resources."""

    # create router config in mock S3 bucket
    # TODO: Should use AppConfig. For now, writing out router config to
    # an S3 url to pass in as the ROUTER_CFG_URL env variable.
    router_file = files("tests.resources").joinpath("test_router.yaml")
    with open(router_file) as f:
        router_cfg = f.read()
    s3_client = boto3.client("s3")
    s3_client.create_bucket(
        Bucket=TEST_BUCKET,
        CreateBucketConfiguration={
            "LocationConstraint": os.environ["AWS_DEFAULT_REGION"]
        },
    )
    with smart_open.open(f"s3://{TEST_BUCKET}/test_router.yaml", "w") as f:
        f.write(router_cfg)

    # create mock SNS topics
    sns_client = boto3.client("sns")
    sns_client.create_topic(
        Name="eval_sbg_l2_readiness", Attributes={"TracingConfig": "Active"}
    )
    sns_client.create_topic(
        Name="eval_m2020_xyz_left_finder", Attributes={"TracingConfig": "Active"}
    )
    sns_client.create_topic(
        Name="eval_nisar_ingest", Attributes={"TracingConfig": "Active"}
    )

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


@respx.mock
@mock_aws
def mocked_lambda_handler_base(event, context):
    """Base lambda handler that mocks AWS and Airflow API calls."""

    setup_mock_resources()
    return lambda_handler_base(event, context)


@respx.mock
@mock_aws
def mocked_lambda_handler_initiator(event, context):
    """Intitiator lambda handler that mocks AWS and Airflow API calls."""

    setup_mock_resources()
    return lambda_handler_initiator(event, context)


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

        # TODO: Should use AppConfig. For now, writing out router config body to
        # the ROUTER_CFG env variable.
        cls.router_file = files("tests.resources").joinpath("test_router.yaml")
        with open(cls.router_file) as f:
            cls.router_cfg = f.read()

        cls.fxn = cls.client.create_function(
            FunctionName=cls.function_name,
            Runtime="python3.11",
            Role=get_role_name(),
            Handler="lambda_function.mocked_lambda_handler_base",
            Code={"ZipFile": get_lambda_code()},
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            Publish=True,
            Environment={"Variables": {"ROUTER_CFG": cls.router_cfg}},
            TracingConfig={"Mode": "Active"},
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


class TestInitiatorLambda:
    mock = mock_aws()

    @classmethod
    def setup_class(cls):
        cls.mock.start()
        cls.lambda_client = boto3.client("lambda")
        cls.function_name = str(uuid4())[0:6]
        cls.logs_client = boto3.client("logs")

        cls.s3_client = boto3.client("s3")
        cls.bucket_name = TEST_BUCKET
        cls.bucket = cls.s3_client.create_bucket(
            Bucket=cls.bucket_name,
            CreateBucketConfiguration={
                "LocationConstraint": os.environ["AWS_DEFAULT_REGION"]
            },
        )

        # create mock SNS topic for initiator
        cls.sns_client = boto3.client("sns")
        cls.sns_topic_initiator = cls.sns_client.create_topic(
            Name="initiator_topic", Attributes={"TracingConfig": "Active"}
        )

        # create mock SQS queues
        cls.sqs_client = boto3.client("sqs")
        cls.sqs_queue_initiator = cls.sqs_client.create_queue(
            QueueName="initiator_queue"
        )
        cls.sqs_queue_initiator_attr = cls.sqs_client.get_queue_attributes(
            QueueUrl=cls.sqs_queue_initiator["QueueUrl"], AttributeNames=["QueueArn"]
        )

        # subscribe SQS queue to SNS topic
        cls.sns_client.subscribe(
            TopicArn=cls.sns_topic_initiator["TopicArn"],
            Protocol="sqs",
            Endpoint=cls.sqs_queue_initiator_attr["Attributes"]["QueueArn"],
        )

        # Set S3 to send ObjectCreated to SNS
        cls.s3_client.put_bucket_notification_configuration(
            Bucket=cls.bucket_name,
            NotificationConfiguration={
                "TopicConfigurations": [
                    {
                        "Id": "SomeID",
                        "TopicArn": cls.sns_topic_initiator["TopicArn"],
                        "Events": ["s3:ObjectCreated:*"],
                    }
                ]
            },
        )

        # we should receive a test message
        messages = cls.sqs_client.receive_message(
            QueueUrl=cls.sqs_queue_initiator["QueueUrl"], MaxNumberOfMessages=10
        )
        assert len(messages["Messages"]) == 1
        logger.debug("SQS message: %s", json.dumps(messages["Messages"], indent=2))
        cls.sqs_client.delete_message(
            QueueUrl=cls.sqs_queue_initiator["QueueUrl"],
            ReceiptHandle=messages["Messages"][0]["ReceiptHandle"],
        )
        message_body = messages["Messages"][0]["Body"]
        sns_message = json.loads(message_body)
        assert sns_message["Type"] == "Notification"
        logger.debug("SNS message: %s", json.dumps(sns_message, indent=2))

        # get S3 notification from SNS message
        s3_message_body = json.loads(sns_message["Message"])
        assert s3_message_body["Event"] == "s3:TestEvent"
        logger.debug("S3 message: %s", json.dumps(s3_message_body, indent=2))

        # create mocked initiator lambda
        cls.fxn = cls.lambda_client.create_function(
            FunctionName=cls.function_name,
            Runtime="python3.11",
            Role=get_role_name(),
            Handler="lambda_function.mocked_lambda_handler_initiator",
            Code={"ZipFile": get_lambda_code()},
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            Publish=True,
            Environment={
                "Variables": {
                    "ROUTER_CFG_URL": f"s3://{cls.bucket_name}/test_router.yaml"
                }
            },
            TracingConfig={"Mode": "Active"},
        )

        # create event source mapping
        cls.lambda_client.create_event_source_mapping(
            EventSourceArn=cls.sqs_queue_initiator_attr["Attributes"]["QueueArn"],
            FunctionName=cls.fxn["FunctionName"],
        )

    @classmethod
    def teardown_class(cls):
        try:
            cls.mock.stop()
        except RuntimeError:
            pass

    def invoke_initiator_via_s3_event(self, bucket, object_prefix):
        """Test invocations of the initiator lambda via S3 event."""

        # Upload file to trigger notification
        self.s3_client.put_object(
            Bucket=bucket, Key=object_prefix, Body=b"hawaii_no_ka_oi"
        )

        # get lambda execution status via logs
        lambda_execution_success = False
        start = time.time()
        while (time.time() - start) < 30:
            result = self.logs_client.describe_log_streams(
                logGroupName=f"/aws/lambda/{self.function_name}"
            )
            log_streams = result.get("logStreams")
            if not log_streams:
                time.sleep(0.5)
                continue
            assert len(log_streams) >= 1
            result = self.logs_client.get_log_events(
                logGroupName=f"/aws/lambda/{self.function_name}",
                logStreamName=log_streams[0]["logStreamName"],
            )
            for event in result.get("events"):
                logger.info("log event: %s", event)
                if '"success":true' in event["message"]:
                    lambda_execution_success = True
                    break
            if lambda_execution_success:
                break
            time.sleep(0.5)
        return lambda_execution_success

    def test_initiator_sbg(self):
        """Test invocations of the initiator lambda via S3 event using SBG test case: submit_to_sns_topic"""

        # Upload file to trigger notification
        assert self.invoke_initiator_via_s3_event(
            self.bucket_name,
            "prefix/SISTER_EMIT_L1B_RDN_20240103T131936_001/SISTER_EMIT_L1B_RDN_20240103T131936_001_OBS.bin",
        )

    def test_initiator_m2020(self):
        """Test invocations of the initiator lambda via S3 event using M2020 test case: submit_to_sns_topic"""

        # Upload file to trigger notification
        assert self.invoke_initiator_via_s3_event(
            self.bucket_name,
            "ids-pipeline/pipes/nonlin_xyz_left/inputque/ML01234567891011121_000RAS_N01234567890101112131415161.VIC-link",
        )

    def test_initiator_nisar_tlm(self):
        """Test invocations of the initiator lambda via S3 event using NISAR TLM test case: submit_to_sns_topic"""

        # Upload file to trigger notification
        assert self.invoke_initiator_via_s3_event(
            self.bucket_name,
            "prefix/NISAR_S198_PA_PA11_M00_P00922_R00_C01_G00_2024_010_17_57_57_714280000.vc29",
        )

    def test_initiator_nisar_ldf(self):
        """Test invocations of the initiator lambda via S3 event using NISAR LDF test case: submit_dag_by_id"""

        # Upload file to trigger notification
        assert self.invoke_initiator_via_s3_event(
            self.bucket_name,
            "prefix/NISAR_S198_PA_PA11_M00_P00922_R00_C01_G00_2024_010_18_03_05_087077000.ldf",
        )
