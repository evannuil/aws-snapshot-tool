aws-snapshot-tool
=================
aws-snapshot-tool is a Python 3 script to make it easy to *roll snapshots of your EBS volumes*.

Simply add a tag to each volume you want snapshots of, configure and install a cronjob for aws-snapshot-tool and you are off. It handles rolling snapshots per day, week and month so that you can set up the retention policy to suit.

Features:
- *Python 3 / boto3 based*: Easy to configure and install as a crontab
- *Simple tag system*: Just add a tag to each of the EBS volumes you want snapshots of
- *Configurable retention policy*: Configure how many day, week, and month snapshots you want to retain
- *Flexible credentials*: Uses the standard boto3 credential chain (environment variables, ~/.aws/credentials, or an IAM instance role) — no need to store keys in the config file
- *SNS notifications*: Works with Amazon SNS out of the box, so you can be notified of snapshot runs
- *Throttling-aware*: Uses boto3 adaptive retries to back off automatically on EC2 API rate limits

Usage
==========
1. Install Python 3 and boto3: `pip3 install -r requirements.txt`
2. Create an SNS topic in AWS and copy the ARN into the config file (optional)
3. Subscribe with an email address to the SNS topic
4. Create a snapshot user in IAM (or use an IAM instance role) and give it the policy from iam.policy.sample
5. Provide credentials via environment variables, ~/.aws/credentials, an IAM role, or the config file
6. Copy config.sample to config.py
7. Decide how many snapshot versions you want for day/week/month and change this in config.py
8. Change the region in config.py
9. Optionally specify a proxy in config.py
10. Give every volume you want snapshots of a tag with a key and a value, and put these in the config file. Default: "MakeSnapshot" with the value "True"
11. Install the script in the cron:

		# chmod +x makesnapshots.py
		# crontab -e
		30 1 * * 1-5 /opt/aws-snapshot-tool/makesnapshots.py day
		30 2 * * 6 /opt/aws-snapshot-tool/makesnapshots.py week
		30 3 1 * * /opt/aws-snapshot-tool/makesnapshots.py month

The script exits non-zero when one or more volumes failed to process, so cron's error reporting (or your monitoring) can pick it up in addition to the SNS report.

Additional Notes
=========
The user or role that executes the script needs the policy from iam.policy.sample.

Snapshots are matched for rotation by their description prefix (`day_snapshot`, `week_snapshot`, `month_snapshot`), so snapshots created by version 3.x of this tool are rotated seamlessly by version 4.x.
