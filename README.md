aws-snapshot-tool
=================

This python scripts makes a snapshot of every volume which has a specific TAG which is defined in the config file. It keeps the 5 (configurable) most current versions of the snapshots.

The access_key and secret_key can be provided as environment vars or put in the config.

For the SNS functionality there must be a topic and the ARN of the topic must be in the config.


The user that executes the script needs the following policies: see iam.policy.sample
