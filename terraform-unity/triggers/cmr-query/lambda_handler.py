import json
import os
from datetime import datetime, timedelta

import boto3
from aws_xray_sdk.core import patch_all, xray_recorder
from cmr import GranuleQuery

from unity_initiator.utils.logger import log_exceptions, logger

patch_all()

INITIATOR_TOPIC_ARN = os.environ["INITIATOR_TOPIC_ARN"]
DYNAMODB_TABLE_NAME = os.environ["DYNAMODB_TABLE_NAME"]


def submit_urls_and_bookkeep(sns_client, urls_to_send, table, granules_to_save):
    # batch submit urls to initiator topic
    with xray_recorder.capture("publish_url_to_initiator_topic"):
        res = sns_client.publish(
            TopicArn=INITIATOR_TOPIC_ARN,
            Subject="Scheduled Task",
            Message=json.dumps([{"payload": i} for i in urls_to_send]),
        )

    # batch save submitted granules to table so they are not resubmitted in the future
    with xray_recorder.capture("update_url_in_dynamodb_table"):
        with table.batch_writer() as writer:
            for granule in granules_to_save:
                writer.put_item(Item=granule)

    return res


@log_exceptions
def lambda_handler(event, context):
    logger.info("event: %s", json.dumps(event, indent=2))
    logger.info("context: %s", context)

    # get dynamodb client
    db_client = boto3.client("dynamodb")
    sns_client = boto3.client("sns")

    # create table (or get if already exists) that will be used to track
    # granules that have already been sumbmitted to the initiator
    if DYNAMODB_TABLE_NAME not in db_client.list_tables()["TableNames"]:
        with xray_recorder.capture("create_dynamodb_table"):
            db_client.create_table(
                TableName=DYNAMODB_TABLE_NAME,
                KeySchema=[{"AttributeName": "title", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "title", "AttributeType": "S"}],
                ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            )
            logger.info("Created table %s.", DYNAMODB_TABLE_NAME)
    table = boto3.resource("dynamodb").Table(DYNAMODB_TABLE_NAME)

    # check required params
    if event.get("provider_id", None) is None:
        raise RuntimeError("Failed to find provider_id parameter.")
    if event.get("concept_id", None) is None:
        raise RuntimeError("Failed to find concept_id parameter.")
    if event.get("seconds_back", None) is None:
        raise RuntimeError("Failed to find seconds_back parameter.")

    # determine start and end timerange
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(seconds=event["seconds_back"])
    logger.info("start_time: %s", start_time)
    logger.info("end_time: %s", end_time)

    # query CMR
    with xray_recorder.capture("query_cmr"):
        api = (
            GranuleQuery()
            .provider(event["provider_id"])
            .concept_id(event["concept_id"])
        )
        api.temporal(start_time.isoformat("T"), end_time.isoformat("T"))
        hits_count = api.hits()
        logger.info("total hits: %s", hits_count)

    # loop over granules and collect ones that haven't been submitted to the
    # initiator yet
    urls_to_send = []
    granules_to_save = []
    for granule in api.get_all():
        if (
            table.get_item(Key={"title": granule["title"]}).get("Item", None)
            is not None
        ):
            logger.info(
                "Skipping granule %s. Already exists in table.", granule["title"]
            )
            continue
        if len(granule["links"]) == 0:
            raise RuntimeError(
                f"No links found: {json.dumps(granule, indent=2, sort_keys=True)}"
            )
        urls = list(
            filter(
                lambda x: x["rel"] == "http://esipfed.org/ns/fedsearch/1.1/data#",
                granule["links"],
            )
        )
        if len(urls) == 0:
            raise RuntimeError(
                f"No data found: {json.dumps(granule, indent=2, sort_keys=True)}"
            )
        logger.info("url: %s", urls[0]["href"])
        urls_to_send.append(urls[0]["href"])
        granules_to_save.append(granule)

    # publish urls to the initiator
    res = "No new granules were found."
    if len(urls_to_send) > 0:
        res = submit_urls_and_bookkeep(
            sns_client, urls_to_send, table, granules_to_save
        )

    return {"success": True, "response": res}
