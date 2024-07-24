import json
import os
from datetime import datetime, timedelta

import boto3
from cmr import GranuleQuery
from unity_intiator.utils.logger import logger

INITIATOR_TOPIC_ARN = os.environ["INITIATOR_TOPIC_ARN"]
DYNAMODB_TABLE_NAME = os.environ["DYNAMODB_TABLE_NAME"]


def lambda_handler(event, context):
    logger.info(f"event: {json.dumps(event, indent=2)}")
    logger.info(f"context: {context}")

    # get dynamodb client
    db_client = boto3.client("dynamodb")
    sns_client = boto3.client("sns")

    # create table (or get if already exists) that will be used to track
    # granules that have already been sumbmitted to the initiator
    if DYNAMODB_TABLE_NAME not in db_client.list_tables()["TableNames"]:
        db_client.create_table(
            TableName=DYNAMODB_TABLE_NAME,
            KeySchema=[{"AttributeName": "title", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "title", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        logger.info(f"Created table {DYNAMODB_TABLE_NAME}.")
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
    logger.info(f"start_time: {start_time}")
    logger.info(f"end_time: {end_time}")

    # query CMR
    api = GranuleQuery().provider(event["provider_id"]).concept_id(event["concept_id"])
    api.temporal(start_time.isoformat("T"), end_time.isoformat("T"))
    hits_count = api.hits()
    logger.info(f"total hits: {hits_count}")

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
                f"Skipping granule {granule['title']}. Already exists in table."
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
        logger.info(f"url: {urls[0]}")
        urls_to_send.append(urls[0])
        granules_to_save.append(granule)

    # publish urls to the initiator
    res = sns_client.publish(
        TopicArn=INITIATOR_TOPIC_ARN,
        Subject="Scheduled Task",
        Message=json.dumps({"payload": urls_to_send}),
    )

    # save submitted granules to table so they are not resubmitted in the future
    with table.batch_writer() as writer:
        for granule in granules_to_save:
            writer.put_item(Item=granule)

    return {"success": True, "response": res}
