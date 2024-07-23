import json
import os

import boto3
from cmr import GranuleQuery

INITIATOR_TOPIC_ARN = os.environ["INITIATOR_TOPIC_ARN"]


def lambda_handler(event, context):
    print(f"event: {json.dumps(event, indent=2)}")
    print(f"context: {context}")

    # implement your adaptation-specific trigger code here and submit payloads
    # to the SNS topic as either a list of payloads or a single payload. Below
    # is an example of a single payload.
    # Finally return True if it successful. False otherwise.

    api = GranuleQuery().provider("GES_DISC").concept_id("C1701805619-GES_DISC")
    api.temporal("2024-07-17T00:00:00Z", "2024-07-17T23:59:59Z")
    hits_count = api.hits()
    print(f"total hits: {hits_count}")
    for granule in api.get_all():
        links = granule["links"]
        if len(links) == 0:
            raise RuntimeError(
                f"No links found: {json.dumps(granule, indent=2, sort_keys=True)}"
            )
        url = None
        for link in links:
            if link["rel"] == "http://esipfed.org/ns/fedsearch/1.1/data#":
                url = link["href"]
                break
        if url is None:
            raise RuntimeError(
                f"No data found: {json.dumps(granule, indent=2, sort_keys=True)}"
            )
        print(url)

    client = boto3.client("sns")
    res = client.publish(
        TopicArn=INITIATOR_TOPIC_ARN,
        Subject="Scheduled Task",
        Message=json.dumps(
            {
                "payload": "s3://bucket/prefix/NISAR_S198_PA_PA11_M00_P00922_R00_C01_G00_2024_010_17_57_57_714280000.vc25"
            }
        ),
    )
    return {"success": True, "response": res}
