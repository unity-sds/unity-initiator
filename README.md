<!-- Header block for project -->
<hr>

<div align="center">

![logo](https://user-images.githubusercontent.com/3129134/163255685-857aa780-880f-4c09-b08c-4b53bf4af54d.png)

<h1 align="center">Unity Initiator</h1>
<!-- ☝️ Replace with your repo name ☝️ -->

</div>

<pre align="center">A framework for implementing triggers and evaluators in the Unity SDS</pre>
<!-- ☝️ Replace with a single sentence describing the purpose of your repo / proj ☝️ -->

<!-- Header block for project -->

[![Python package](https://github.com/unity-sds/unity-initiator/actions/workflows/python-package.yml/badge.svg)](https://github.com/unity-sds/unity-initiator/actions/workflows/python-package.yml)

![initiators_diagram](https://github.com/unity-sds/unity-initiator/assets/387300/a698a19d-7204-486f-a942-7c9b6f789cb1)
<!-- ☝️ Screenshot of your software (if applicable) via ![](https://uri-to-your-screenshot) ☝️ -->

### What is Unity SDS?

Quite simply, an SDS (Science Data System) is an orchestrated set of networked compute and storage resources that is adapted to process science data through a pipeline. As described by [Hua et al. [2022]](#1):
> Science Data Systems (SDSes) provide the capability to develop, test, process, and analyze instrument observational data efficiently, systematically, and at large scales. SDSes ingest the raw satellite instrument observations and process them from low‐level instrument values into higher level observational measurement values that compose the science data products.

The [Unity SDS](https://github.com/unity-sds) is an implementation of an SDS by the Unity project at NASA Jet Propulsion Laboratory.

### What are triggers?

Trigger events are events that could potentially kick off processing in an SDS. Examples of trigger events are:

1. A raw data file is deposited into a location e.g. an S3 bucket or a local directory.
1. A scheduled task runs and finds a new raw data file has been published to a data repository e.g. CMR (Common Metadata Repository), ASF DAAC's Vertex, etc.

The different types of trigger events lend themselves to particular trigger implementations. Taking #1 as an example and specifically using the S3 bucket use case, an implementation of that trigger could be to use the native S3 event notification capability to notify the SDS that a new file was deposited in the bucket. For the local directory use case, the trigger implementation could be to use the python [watchdog library](https://pypi.org/project/watchdog/) to monitor a local directory and to notify the SDS when a new file has been deposited there.

Taking #2 as an example, an implementation of that trigger would be a cron job running on a local machine that would start up a script that queries for new data using some remote API call which would then notify the SDS. An "all-in" cloud implementation of this trigger would be to use AWS EventBridge as the cron scheduler and AWS Lambda as the "script" that performs the querying and SDS notification.

These are just an initial subset of the different types of trigger events and their respective trigger implementations. This unity-initiator github repository provides [examples](terraform-unity/triggers) of some of these trigger implementations. More importantly, however, the unity-initator provides the common interface to which any trigger implementation can notify the SDS of a triggering event. This common interface is called the initiator topic (implemented as an SNS topic) and the following screenshot from the above architecture diagram shows their interaction:

![triggers](https://github.com/unity-sds/unity-initiator/assets/387300/f7d26a4e-908d-4b0b-913b-4e7704a8a2a1)

Trigger events by themselves don't automatically mean that SDS processing is ready to proceed. That's what evaluators are for.

### What are evaluators?

As described by [Hua et al. [2022]](#1):
> A fundamental capability of an SDS is to systematically process science data through a series of data transformations from raw instrument data to geophysical measurements. Data are first made available to the SDS from GDS to be processed to higher level data products. The data transformation steps may utilize ancillary and auxiliary files as well as production rules that stipulate conditions for when each step should be executed.

In an SDS, evaluators are functions (irrespective of how they are deployed and called) that perform adaptation-specific evaluation to determine if the next step in the processing pipeline is ready for execution.

As an example, the following shows the input-output diagram for the NISAR L-SAR L0B PGE (a.k.a. science algorithm):

![nisar_l0b](https://github.com/unity-sds/unity-initiator/assets/387300/395e73da-adb8-459c-a611-8fa9beb6f77f)

The NISAR L-SAR L0B PGE is only executed when the evaluator function determines that:

1. All input L0A files necessary to cover the L0B granule timespan are present in the SDS
2. The following ancillary files for the input data timespan exist in the SDS and are of the correct fidelity (forecast vs. near vs. medium vs. precise): LRCLK-UTC, orbit ephemeris, radar pointing, radar config, BFPQ lookup tables, LSAR channel data
3. Metadata regarding the NISAR-specific observation plan, CTZ (cycle time zero) and other orbit-related fields fields are available from these ancillary files: dCOP, oROST, STUF

When evaluation is successful, the L0B PGE job is submitted, L0B products are produced, and evaluators for downstream PGEs (e.g. L1) are executed.

The unity-initiator github repository provides [examples](terraform-unity/evaluators) of evaluators that can be used as templates to adapt and deploy for a mission or project. More importantly, the unity-initiator provides the set of common interfaces for which any adaptation-specific evaluator can be called as a result of a trigger event. Currently there are 2 supported interfaces but this repository is organized and structured to easily extend to new interfaces:

1. Trigger event information published to an evaluator SNS topic + SQS queue executes an evaluator implemented as an AWS Lambda function (submit_to_sns_topic action)
2. Trigger event information submitted as DAG run for an evaluator implemented in SPS (submit_dag_by_id action)

The following screenshot shows examples of both of these interfaces:

![evaluators](https://github.com/unity-sds/unity-initiator/assets/387300/b36aae2c-16a7-4b94-8721-020b7b375f25)

It is the responsibility of the initiator to perform the routing of triggers to their respective evaluators.

### What is the Unity initiator?

The Unity initiator is the set of compute resources that enable the routing of trigger events to their respective evaluators. It is agnostic of the trigger event source and agnostic of the adaptation-specific evaluator code. It is completely driven by configuration (a.k.a. router configuration YAML). The following screenshot shows the current architecture for the initiator:

![initiator](https://github.com/unity-sds/unity-initiator/assets/387300/74f7c2cb-8542-4ad8-9212-e720077373c0)

The initiator topic, an SNS topic, is the common interface that all triggers will submit events to. The initiator topic is subscribed to by the initiator SQS queue (complete with dead-letter queue for resiliency) which in turn is subscribed to by the router Lambda function. How the router Lambda routes payloads of the trigger events is defined by the router configuration YAML. The full YAML schema for the router configuration is located [here](src/unity_initiator/resources/routers_schema.yaml).

#### How the router works

In the context of trigger events where a new file is detected (payload_type=`url`), the router Lambda extracts the URL of the new file, instantiates a router object and attempts to match it up against of set of regular expressions defined in the router configuration file. Let's consider this minimal router configuration YAML file example:

```
initiator_config:
  name: minimal config example
  payload_type:
    url:
      - regexes:
            - '/(?P<id>(?P<Mission>NISAR)_S(?P<SCID>\d{3})_(?P<Station>\w{2,3})_(?P<Antenna>\w{3,4})_M(?P<Mode>\d{2})_P(?P<Pass>\d{5})_R(?P<Receiver>\d{2})_C(?P<Channel>\d{2})_G(?P<Group>\d{2})_(?P<FileCreationDateTime>\d{4}_\d{3}_\d{2}_\d{2}_\d{2}_\d{6})\d{3}\.vc(?P<VCID>\w{2}))$'
        evaluators:
          - name: eval_nisar_ingest
            actions:
              - name: submit_to_sns_topic
                params:
                  topic_arn: arn:aws:sns:hilo-hawaii-1:123456789012:eval_nisar_ingest
                  on_success:
                    actions:
                      - name: submit_dag_by_id
                        params:
                          dag_id: submit_nisar_tlm_ingest
                          airflow_base_api_endpoint: xxx
                          airflow_username: <SSM parameter, e.g. /unity/airflow/username> <ARN to username entry in AWS Secrets Manager>
                          airflow_password: <SSM parameter, e.g. /unity/airflow/password> <ARN to password entry in Secrets Manager>
```

and a trigger event payload for a new file that was triggered:

```
{
  "payload": "s3://test_bucket/prefix/NISAR_S198_PA_PA11_M00_P00922_R00_C01_G00_2024_010_17_57_57_714280000.vc29"
}
```

The router will iterate over the set of url configs and attempt to match the URL against its set of regexes. If a match is successful, the router will iterate over the configured evaluators configs and perform the configured action to submit the URL payload to the evaluator interface (either SNS topic or DAG submission). In this case, the router sees that the action is `submit_to_sns_topic` and thus publishes the URL payload (and the regular expression captured groups as `payload_info`) to the SNS topic (`topic_arn`) configured in the action's parameters. In addition to the payload URL and the payload info, the router also includes the `on_success` parameters configured for the action. This will propagate pertinent info to the underlying evaluator code which would be used if evaluation is successful. In this case, if the evaulator successfully evaluates that everything is ready for this input file, it can proceed to submit a DAG run for the `submit_nisar_tlm_ingest` DAG in the underlying SPS.

Let's consider another example but this time the configured action is to submit a DAG run instead of publishing to an evaluator's SNS topic:

```
initiator_config:
  name: minimal config example
  payload_type:
    url:
      - regexes:
            - '/(?P<id>(?P<Mission>NISAR)_S(?P<SCID>\d{3})_(?P<Station>\w{2,3})_(?P<Antenna>\w{3,4})_M(?P<Mode>\d{2})_P(?P<Pass>\d{5})_R(?P<Receiver>\d{2})_C(?P<Channel>\d{2})_G(?P<Group>\d{2})_(?P<FileCreationDateTime>\d{4}_\d{3}_\d{2}_\d{2}_\d{2}_\d{5})(?P<R>\d{1,4})\.ldf)$'
        evaluators:
          - name: eval_nisar_l0a_readiness
            actions:
              - name: submit_dag_by_id
                params:
                  dag_id: eval_nisar_l0a_readiness
                  airflow_base_api_endpoint: https://example.com/api/v1
                  airflow_username: <SSM parameter, e.g. /unity/airflow/username> <ARN to username entry in AWS Secrets Manager>
                  airflow_password: <SSM parameter, e.g. /unity/airflow/password> <ARN to password entry in Secrets Manager>
                  on_success:
                    actions:
                      - name: submit_dag_by_id
                        params:
                          dag_id: submit_nisar_l0a_te_dag
                          # These are commented out because by default they will be pulled from the above configuration since we're in airflow.
                          # Otherwise these can be uncommented out for explicit configuration (e.g. another SPS cluster)
                          #airflow_base_api_endpoint: xxx
                          #airflow_username: <ARN to username entry in AWS Secrets Manager>
                          #airflow_password: <ARN to password entry in Secrets Manager>
```

and a trigger event payload for a new file that was triggered:

```
{
  "payload": "s3://test_bucket/prefix/NISAR_S198_PA_PA11_M00_P00922_R00_C01_G00_2024_010_17_57_57_714280000.ldf"
}
```

In this case, the router sees that the action is `submit_dag_by_id` and thus makes a REST call to SPS to submit the URL payload, payload info, and `on_success` parameters as a DAG run. If the evaulator, running now as a DAG in SPS instead of an AWS Lambda function, successfully evaluates that everything is ready for this input file, it can proceed to submit a DAG run for the `submit_nisar_l0a_te_dag` DAG in the underlying SPS.

<!-- ☝️ Replace with a more detailed description of your repository, including why it was made and whom its intended for.  ☝️ -->

<!-- example links>
[Website](INSERT WEBSITE LINK HERE) | [Docs/Wiki](INSERT DOCS/WIKI SITE LINK HERE) | [Discussion Board](INSERT DISCUSSION BOARD LINK HERE) | [Issue Tracker](INSERT ISSUE TRACKER LINK HERE)
-->

## Features

* Examples of triggers
* Example templates of evaluators
* Configuration-driven routing of trigger events to evaluators
* Terraform script for easy of deploying the initiator, triggers, and evaluators

<!-- ☝️ Replace with a bullet-point list of your features ☝️ -->

## Contents

* [Features](#features)
* [Contents](#contents)
* [Quick Start](#quick-start)
  * [Requirements](#requirements)
  * [Setting Up the End-to-End Demo](#setting-up-the-end-to-end-demo)
    * [Deploying the Initiator](#deploying-the-initiator)
    * [Deploying an Example Evaluator (SNS topic-\>SQS queue-\>Lambda)](#deploying-an-example-evaluator-sns-topic-sqs-queue-lambda)
    * [Deploying an S3 Event Notification Trigger](#deploying-an-s3-event-notification-trigger)
    * [Verify End-to-End Functionality (part 1)](#verify-end-to-end-functionality-part-1)
    * [Deploying an EventBridge Scheduler Trigger](#deploying-an-eventbridge-scheduler-trigger)
    * [Verify End-to-End Functionality (part 2)](#verify-end-to-end-functionality-part-2)
    * [Tear Down](#tear-down)
  * [Setup Instructions for Development](#setup-instructions-for-development)
  * [Build Instructions](#build-instructions)
  * [Test Instructions](#test-instructions)
* [Changelog](#changelog)
* [Frequently Asked Questions (FAQ)](#frequently-asked-questions-faq)
* [Contributing](#contributing)
* [License](#license)
* [References](#references)

## Quick Start

This guide provides a quick way to get started with our project. Please see our [docs]([INSERT LINK TO DOCS SITE / WIKI HERE]) for a more comprehensive overview.

### Requirements

* python 3.9+
* docker
* hatch
* terraform
* all other dependencies (defined in the [pyproject.toml](pyproject.toml)) will be installed and managed by hatch

<!-- ☝️ Replace with a numbered list of your requirements, including hardware if applicable ☝️ -->

### Setting Up the End-to-End Demo

#### Deploying the Initiator

1. Clone repo:

   ```
   git clone https://github.com/unity-sds/unity-initiator.git
   ```

1. Change directory to the location of the inititator terraform:

   ```
   cd unity-initiator/terraform-unity/initiator/
   ```

1. Copy a sample router configuration YAML file to use for deployment and update the AWS region and AWS account ID to match your AWS environment. We will be using the NISAR TLM test case for this demo so we also rename the SNS topic ARN for it accordingly:

   ```
   cp ../../tests/resources/test_router.yaml .
   export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --output text | awk '{print $1}')
   export AWS_REGION=$(aws configure get region)
   sed -i "s/hilo-hawaii-1/${AWS_REGION}/g" test_router.yaml
   sed -i "s/123456789012:eval_nisar_ingest/${AWS_ACCOUNT_ID}:uod-dev-eval_nisar_ingest-evaluator_topic/g" test_router.yaml
   ```

1. You will need an S3 bucket for terraform to stage the router Lambda zip file during deployment. Create one or reuse an existing one and set an environment variable for it:

   ```
   export CODE_BUCKET=<some S3 bucket name>
   ```

1. You will need an S3 bucket to store the router configuration YAML file. Create one or reuse an existing one (could be the same one in the previous step) and set an environment variable for it:

   ```
   export CONFIG_BUCKET=<some S3 bucket name>
   ```

1. Set a deployment name:

   ```
   export DEPLOYMENT_NAME=gmanipon-test
   ```

1. Initialize terraform:

   ```
   terraform init
   ```

1. Run terraform apply:

   ```
   terraform apply \
     --var deployment_name=${DEPLOYMENT_NAME} \
     --var code_bucket=${CODE_BUCKET} \
     --var config_bucket=${CONFIG_BUCKET} \
     --var router_config=test_router.yaml \
     -auto-approve
   ```

   **Take note of the `initiator_topic_arn` that is output by terraform. It will be used when setting up any triggers.**

#### Deploying an Example Evaluator (SNS topic->SQS queue->Lambda)

1. Change directory to the location of the sns_sqs_lambda evaluator terraform:

   ```
   cd ../evaluators/sns_sqs_lambda/
   ```

1. Set the name of the evaluator to our NISAR example:

   ```
   export EVALUATOR_NAME=eval_nisar_ingest
   ```

1. Note the implementation of the evaluator code. It currently doesn't do any real evaluation but simply returns that evaluation was successful:

   ```
   cat data.tf
   ```

1. Initialize terraform:

   ```
   terraform init
   ```

1. Run terraform apply:

   ```
   terraform apply \
     --var evaluator_name=${EVALUATOR_NAME} \
     -auto-approve
   ```

   **Take note of the `evaluator_topic_arn` that is output by terraform. It should match the topic ARN in the test_router.yaml file you used during the initiator deployment. If they match then the router Lambda is now able to submit payloads to this evaluator SNS topic.**

#### Deploying an S3 Event Notification Trigger

1. Change directory to the location of the s3_bucket_notification trigger terraform:

   ```
   cd ../../triggers/s3_bucket_notification/
   ```

1. You will need an S3 bucket to configure event notification on. Create one or reuse an existing one (could be the same one in the previous steps) and set an environment variable for it:

   ```
   export ISL_BUCKET=<some S3 bucket name>
   ```

1. Specify an S3 prefix from which S3 event notifications will be emitted when objects are created:

   ```
   export ISL_BUCKET_PREFIX=incoming/
   ```

1. Export the `initiator_topic_arn` that was output from the initiator terraform deployment:

   ```
   export INITIATOR_TOPIC_ARN=<initiator topic ARN>
   ```

1. Initialize terraform:

   ```
   terraform init
   ```

1. Run terraform apply:

   ```
   terraform apply \
     --var isl_bucket=${ISL_BUCKET} \
     --var isl_bucket_prefix=${ISL_BUCKET_PREFIX} \
     --var initiator_topic_arn=${INITIATOR_TOPIC_ARN} \
     -auto-approve
   ```

1. Verify that the S3 event notification was correctly hooked up to the initiator by looking at the initiator Lambda's CloudWatch logs for a entry similar to this:
   ![cloudwatch_logs_s3_testevent](https://github.com/unity-sds/unity-initiator/assets/387300/460a0d0b-ee01-480d-afab-ba70185341fc)

#### Verify End-to-End Functionality (part 1)

1. Create some fake NISAR TLM files and stage them up to the ISL bucket under the ISL prefix:

   ```
   for i in $(echo 24 25 29); do
     echo 'Hawaii, No Ka Oi!' > NISAR_S198_PA_PA11_M00_P00922_R00_C01_G00_2024_010_17_57_57_714280000.vc${i}
     aws s3 cp NISAR_S198_PA_PA11_M00_P00922_R00_C01_G00_2024_010_17_57_57_714280000.vc${i} s3://${ISL_BUCKET}/${ISL_BUCKET_PREFIX}
     rm NISAR_S198_PA_PA11_M00_P00922_R00_C01_G00_2024_010_17_57_57_714280000.vc${i}
   done
   ```

1. Verify that the `eval_nisar_ingest` evaluator Lambda function was called successfully for each of those staged files by looking at its CloudWatch logs for entries similar to this:
   ![eval_log_1](https://github.com/unity-sds/unity-initiator/assets/387300/34a273a5-5992-46f8-982b-0a0ec37d1798)

#### Deploying an EventBridge Scheduler Trigger

1. Change directory to the location of the s3_bucket_notification trigger terraform:

   ```
   cd ../scheduled_task/
   ```

1. Note the implementation of the trigger lambda code. It currently hard codes a payload URL however in a real implementation, code would be written to query for new files from some REST API, database, etc. Here we simulate that and simply return a NISAR TLM file:

   ```
   cat data.tf
   ```

1. Initialize terraform:

   ```
   terraform init
   ```

1. Run terraform apply. Note the DEPLOYMENT_NAME and INITIATOR_TOPIC_ARN environment variables should have been set in the previous steps. If not set them again:

   ```
   terraform apply \
     --var deployment_name=${DEPLOYMENT_NAME} \
     --var initiator_topic_arn=${INITIATOR_TOPIC_ARN} \
     -auto-approve
   ```

#### Verify End-to-End Functionality (part 2)

1. The deployed EventBridge scheduler runs the trigger Lambda function with schedule expression of `rate(1 minute)`. After a minute, verify that the `eval_nisar_ingest` evaluator Lambda function was called successfully for each of those scheduled invocations by looking at its CloudWatch logs for entries similar to this:
   ![eval_log_2](https://github.com/unity-sds/unity-initiator/assets/387300/cae82e10-a736-43b7-8957-790fc29b5fea)

#### Tear Down

1. Simply go back into each of the terraform directories for which `terraform apply` was run and run `terraform destroy`.

### Setup Instructions for Development

1. Clone repo:

   ```
   git clone https://github.com/unity-sds/unity-initiator.git
   ```

1. Install hatch:

   ```
   pip install hatch
   ```

1. Build virtualenv and install dependencies:

   ```
   cd unity-initiator
   hatch env create
   ```

1. Install dev tools:

   ```
   ./scripts/install_dev_tools.sh
   ```

1. Test pre-commit run:

   ```
   pre-commit run --all-files
   ```

   You should see the following output:

   ```
   check for merge conflicts...............................................................Passed
   check for broken symlinks...........................................(no files to check)Skipped
   trim trailing whitespace................................................................Passed
   isort...................................................................................Passed
   black...................................................................................Passed
   ruff....................................................................................Passed
   bandit..................................................................................Passed
   prospector..............................................................................Passed
   Terraform fmt...........................................................................Passed
   Terraform docs..........................................................................Passed
   Terraform validate......................................................................Passed
   Lock terraform provider versions........................................................Passed
   Terraform validate with tflint..........................................................Passed
   Terraform validate with tfsec (deprecated, use "terraform_trivy").......................Passed
   ```

<!-- ☝️ Replace with a numbered list of how to set up your software prior to running ☝️ -->

### Build Instructions

1. Follow [Setup Instructions for Development](#setup-instructions-for-development) above.
1. Enter environment:

   ```
   hatch shell
   ```

1. Build:

   ```
   hatch build
   ```

   Wheel and tarballs will be built in the `dist/` directory:

   ```
   $ tree dist
   dist
   ├── unity_initiator-0.0.1-py3-none-any.whl
   └── unity_initiator-0.0.1.tar.gz

   1 directory, 2 files
   ```

<!-- ☝️ Replace with a numbered list of your build instructions, including expected results / outputs with optional screenshots ☝️ -->

### Test Instructions

1. Follow [Setup Instructions for Development](#setup-instructions-for-development) above.
1. Enter environment:

   ```
   hatch shell
   ```

1. Run tests:

   ```
   hatch run pytest
   ```

   For more information during test runs, set the log level accordingly. For example:

   ```
   hatch run pytest -s -v --log-cli-level=INFO --log-level=INFO
   ```

<!-- ☝️ Replace with a numbered list of your test instructions, including expected results / outputs with optional screenshots ☝️ -->

## Changelog

See our [CHANGELOG.md](CHANGELOG.md) for a history of our changes.

See our [releases page]([https://github.com/unity-sds/unity-initiator/releases]) for our key versioned releases.

<!-- ☝️ Replace with links to your changelog and releases page ☝️ -->

## Frequently Asked Questions (FAQ)

No questions yet. Propose a question to be added here by reaching out to our contributors! See support section below.

<!-- ☝️ Replace with a list of frequently asked questions from your project, or post a link to your FAQ on a discussion board ☝️ -->

## Contributing

Interested in contributing to our project? Please see our: [CONTRIBUTING.md](CONTRIBUTING.md)

For guidance on how to interact with our team, please see our code of conduct located at: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

For guidance on our governance approach, including decision-making process and our various roles, please see our governance model at: [GOVERNANCE.md](GOVERNANCE.md)

## License

`unity-initiator` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## References

<a id="1">[1]</a>
Hua, H., Manipon, G. and Shah, S. (2022).
Scaling Big Earth Science Data Systems Via Cloud Computing.
In Big Data Analytics in Earth, Atmospheric, and Ocean Sciences (eds T. Huang, T.C. Vance and C. Lynnes).
<https://doi.org/10.1002/9781119467557.ch3>
