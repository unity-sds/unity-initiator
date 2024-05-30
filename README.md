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

Taking #2 as an example, an implementation of that trigger would be a cron job running on a local machine that would start up a script that queries for new data using some remote API call which would then notify the SDS. An "all-in" cloud implementation of this trigger would be to use AWS EventBridge as the cron scheduler and AWS Lambda as the "script" that does the querying and SDS notification.

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
3. Metadata regarding NISAR-specific observation plan, CTZ (cycle time zero) and other orbit-related fields fields are available from these ancillary files: dCOP, oROST, STUF

Reality is that there are a few more things that are checked for during this evaluator run but the gist of the evaluation are the steps above. When evaluation is successful, the L0B PGE job is submitted, L0B products are produced, and evaluators for downstream PGEs (e.g. L1) are executed.

As with triggers above, the unity-initiator github repository provides [examples](terraform-unity/evaluators) of evaluators that can be used as templates to adapt for a mission/project and deployed. More importantly, the unity-initiator provides the set of common interaces for which any adaptation-specific evaluator can be called as a result of a trigger event. Currently there are only 2 supported interfaces but this repository is set up to easily add new interfaces:

1. Trigger event information published to an evaluator SNS topic + SQS queue executes an evaluator implemented as an AWS Lambda function (submit_to_sns_topic action)
2. Trigger event information submitted as DAG run for an evaluator implemented in SPS (submit_dag_by_id action)

The following screenshot shows examples of both of these interfaces:

![evaluators](https://github.com/unity-sds/unity-initiator/assets/387300/b36aae2c-16a7-4b94-8721-020b7b375f25)

It is the responsibility of the initiator to perform the routing of triggers to their respective evaluators.

### What is the Unity initiator?
The Unity initiator is the set of compute resources that enable the routing of trigger events to their respective evaluators. It is agnostic of the trigger event source and agnostic of the adaptation-specific evaluator code. It is completely driven by configuration (a.k.a. router configuration YAML). The following screenshot shows the current architecture for the initiator:

![initiator](https://github.com/unity-sds/unity-initiator/assets/387300/74f7c2cb-8542-4ad8-9212-e720077373c0)

The initiator topic, an SNS topic, is the common interface that all triggers will submit events to. The initiator topic is subscribed to by the initiator SQS queue (complete with dead-letter queue for resiliency) which in turn is subscribed to by the router Lambda function. How the router Lambda routes payloads of the trigger events is described the router configuration YAML. The full YAML schema for the router configuration is located [here](src/unity_initiator/resources/routers_schema.yaml).

#### How the router works
In the context of trigger events where a new file is detected (payload_type=`url`), the router Lambda extracts the URL of the new file, instantiates a router object and attempts to match it up against of set of regular expressions defined in the router configuration file. Let's consider this minimal router configuration YAML file example:

```
initiator_config:
  name: minimal config example
  payload_type:
    url:
      - regexes:
            - !!python/regexp '/(?P<id>(?P<Mission>NISAR)_S(?P<SCID>\d{3})_(?P<Station>\w{2,3})_(?P<Antenna>\w{3,4})_M(?P<Mode>\d{2})_P(?P<Pass>\d{5})_R(?P<Receiver>\d{2})_C(?P<Channel>\d{2})_G(?P<Group>\d{2})_(?P<FileCreationDateTime>\d{4}_\d{3}_\d{2}_\d{2}_\d{2}_\d{6})\d{3}\.vc(?P<VCID>\w{2}))$'
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
            - !!python/regexp '/(?P<id>(?P<Mission>NISAR)_S(?P<SCID>\d{3})_(?P<Station>\w{2,3})_(?P<Antenna>\w{3,4})_M(?P<Mode>\d{2})_P(?P<Pass>\d{5})_R(?P<Receiver>\d{2})_C(?P<Channel>\d{2})_G(?P<Group>\d{2})_(?P<FileCreationDateTime>\d{4}_\d{3}_\d{2}_\d{2}_\d{2}_\d{5})(?P<R>\d{1,4})\.ldf)$'
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

* [Quick Start](#quick-start)
* [Changelog](#changelog)
* [FAQ](#frequently-asked-questions-faq)
* [Contributing Guide](#contributing)
* [License](#license)
* [Support](#support)

## Quick Start

This guide provides a quick way to get started with our project. Please see our [docs]([INSERT LINK TO DOCS SITE / WIKI HERE]) for a more comprehensive overview.

### Requirements

* python 3.9+
* docker
* hatch
* terraform
* all other dependencies (defined in the [pyproject.toml](pyproject.toml)) will be installed and managed by hatch

<!-- ☝️ Replace with a numbered list of your requirements, including hardware if applicable ☝️ -->

### Deploying the Initiator

1. Clone repo:
   ```
   git clone https://github.com/unity-sds/unity-initiator.git
   ```
1. Change directory to the location of the inititator terraform:
   ```
   cd unity-initiator/terraform-unity/initiator/
   ```
1. Initialize terraform:
   ```
   terraform init
   ```
1. Copy a sample router configuration YAML file to use for deployment and update the AWS region and AWS account ID to match your AWS environment:
   ```
   cp ../../tests/resources/test_router.yaml .
   export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --output text | awk '{print $1}')
   export AWS_REGION=$(aws configure get region)
   sed -i "s/hilo-hawaii-1/${AWS_REGION}/g" test_router.yaml
   sed -i "s/123456789012/${AWS_ACCOUNT_ID}/g" test_router.yaml
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
1. Run terraform apply:
   ```
   terraform apply \
     --var deployment_name=${DEPLOYMENT_NAME} \
     --var code_bucket=${CODE_BUCKET} \
     --var config_bucket=${CONFIG_BUCKET} \
     --var router_config=test_router.yaml \
     -auto-approve
   ```
1. 

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

### Run Instructions

1. [INSERT STEP-BY-STEP RUN INSTRUCTIONS HERE, WITH OPTIONAL SCREENSHOTS]

<!-- ☝️ Replace with a numbered list of your run instructions, including expected results ☝️ -->

### Usage Examples

* [INSERT LIST OF COMMON USAGE EXAMPLES HERE, WITH OPTIONAL SCREENSHOTS]

<!-- ☝️ Replace with a list of your usage examples, including screenshots if possible, and link to external documentation for details ☝️ -->

## Changelog

See our [CHANGELOG.md](CHANGELOG.md) for a history of our changes.

See our [releases page]([INSERT LINK TO YOUR RELEASES PAGE]) for our key versioned releases.

<!-- ☝️ Replace with links to your changelog and releases page ☝️ -->

## Frequently Asked Questions (FAQ)

[INSERT LINK TO FAQ PAGE OR PROVIDE FAQ INLINE HERE]
<!-- example link to FAQ PAGE>
Questions about our project? Please see our: [FAQ]([INSERT LINK TO FAQ / DISCUSSION BOARD])
-->

<!-- example FAQ inline format>
1. Question 1
   - Answer to question 1
2. Question 2
   - Answer to question 2
-->

<!-- example FAQ inline with no questions yet>
No questions yet. Propose a question to be added here by reaching out to our contributors! See support section below.
-->

<!-- ☝️ Replace with a list of frequently asked questions from your project, or post a link to your FAQ on a discussion board ☝️ -->

## Contributing

[INSERT LINK TO CONTRIBUTING GUIDE OR FILL INLINE HERE]
<!-- example link to CONTRIBUTING.md>
Interested in contributing to our project? Please see our: [CONTRIBUTING.md](CONTRIBUTING.md)
-->

<!-- example inline contributing guide>
1. Create an GitHub issue ticket describing what changes you need (e.g. issue-1)
2. [Fork](INSERT LINK TO YOUR REPO FORK PAGE HERE, e.g. https://github.com/my_org/my_repo/fork) this repo
3. Make your modifications in your own fork
4. Make a pull-request in this repo with the code in your fork and tag the repo owner / largest contributor as a reviewer

**Working on your first pull request?** See guide: [How to Contribute to an Open Source Project on GitHub](https://kcd.im/pull-request)
-->

[INSERT LINK TO YOUR CODE_OF_CONDUCT.md OR SHARE TEXT HERE]
<!-- example link to CODE_OF_CONDUCT.md>
For guidance on how to interact with our team, please see our code of conduct located at: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
-->

<!-- ☝️ Replace with a text describing how people may contribute to your project, or link to your contribution guide directly ☝️ -->

[INSERT LINK TO YOUR GOVERNANCE.md OR SHARE TEXT HERE]
<!-- example link to GOVERNANCE.md>
For guidance on our governance approach, including decision-making process and our various roles, please see our governance model at: [GOVERNANCE.md](GOVERNANCE.md)
-->

## License

See our: [LICENSE](LICENSE)
<!-- ☝️ Replace with the text of your copyright and license, or directly link to your license file ☝️ -->

## Support

[INSERT CONTACT INFORMATION OR PROFILE LINKS TO MAINTAINERS AMONG COMMITTER LIST]

<!-- example list of contacts>
Key points of contact are: [@github-user-1](link to github profile) [@github-user-2](link to github profile)
-->

<!-- ☝️ Replace with the key individuals who should be contacted for questions ☝️ -->

# unity-initiator

[![PyPI - Version](https://img.shields.io/pypi/v/unity-initiator.svg)](https://pypi.org/project/unity-initiator)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/unity-initiator.svg)](https://pypi.org/project/unity-initiator)

-----

**Table of Contents**

- [Installation](#installation)
- [License](#license)

## Installation

```console
pip install unity-initiator
```

## License

`unity-initiator` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.o

## References
<a id="1">[1]</a>
Hua, H., Manipon, G. and Shah, S. (2022).
Scaling Big Earth Science Data Systems Via Cloud Computing.
In Big Data Analytics in Earth, Atmospheric, and Ocean Sciences (eds T. Huang, T.C. Vance and C. Lynnes).
https://doi.org/10.1002/9781119467557.ch3
