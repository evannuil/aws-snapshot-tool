aws-snapshot-tool
=================

This python scripts makes a snapshot of every volume which has a specific TAG which is defined in the config file. It keeps the 5 (configurable) most current versions of the snapshots.

For the SNS functionality there must be a topic and the ARN of the topic must be in the config.

The user that executes the script needs the following policies: see iam.policy.sample

Usage
==========
1. Install and configure Python and Boto
2. Create a SNS topic in AWS and copy the ARN into the config file
3. Subscribe with a email address to the SNS topic
4. Create a snapshot user in IAM and put the key and secret in the config file
5. Create a security policy for this user (see the iam.policy.sample)
6. Decide how many versions of the snapshots you want and change this in the config (default: 5)
7. Change the Region and Endpoint for AWS in the config file
8. If a there is a proxy you must use fill in the settings, otherwise keep them ''
9. Give every Volume for which you want snapshots a Tag with a Key and a Value and put these in the config file. Default: "MakeSnapshot" and the value "True"
10. put the script in the cron: 

		# chmod +x makesnapshots.py
		# crontab -e
		0 5 * * * /home/ubuntu/scripts/makesnapshots.py
