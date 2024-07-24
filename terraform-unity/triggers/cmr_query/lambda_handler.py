import json
import os
from datetime import datetime, timedelta

import boto3
from cmr import GranuleQuery

INITIATOR_TOPIC_ARN = os.environ["INITIATOR_TOPIC_ARN"]
DYNAMODB_TABLE_NAME = os.environ["DYNAMODB_TABLE_NAME"]


def lambda_handler(event, context):
    print(f"event: {json.dumps(event, indent=2)}")
    print(f"context: {context}")

    # get dynamodb client
    db_client = boto3.client("dynamodb")
    sns_client = boto3.client("sns")

    # get table creating it if necessary
    if DYNAMODB_TABLE_NAME not in db_client.list_tables()["TableNames"]:
        db_client.create_table(
            TableName=DYNAMODB_TABLE_NAME,
            KeySchema=[{"AttributeName": "title", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "title", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        print(f"Created table {DYNAMODB_TABLE_NAME}.")
    table = boto3.resource("dynamodb").Table(DYNAMODB_TABLE_NAME)

    # check required CMR params
    if event.get("provider_id", None) is None:
        raise RuntimeError("Failed to find provider_id parameter.")
    if event.get("concept_id", None) is None:
        raise RuntimeError("Failed to find concept_id parameter.")
    if event.get("seconds_back", None) is None:
        raise RuntimeError("Failed to find seconds_back parameter.")

    # set start and end times
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(seconds=event["seconds_back"])
    print(f"start_time: {start_time}")
    print(f"end_time: {end_time}")

    # query CMR
    api = GranuleQuery().provider(event["provider_id"]).concept_id(event["concept_id"])
    api.temporal(start_time.isoformat("T"), end_time.isoformat("T"))
    hits_count = api.hits()
    print(f"total hits: {hits_count}")
    all_res = []
    for granule in api.get_all():
        if (
            table.get_item(Key={"title": granule["title"]}).get("Item", None)
            is not None
        ):
            print(f"Skipping granule {granule['title']}. Already exists in table.")
            continue
        table.put_item(Item=granule)
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
        print(urls[0])
        all_res.append(
            sns_client.publish(
                TopicArn=INITIATOR_TOPIC_ARN,
                Subject="Scheduled Task",
                Message=json.dumps({"payload": urls[0]}),
            )
        )
    return {"success": True, "response": all_res}
