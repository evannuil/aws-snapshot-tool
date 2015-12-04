aws-snapshot-tool
=================
aws-snapshot-tool is a python script to make it easy to *roll snapshot of your EBS volumes*. 

Simply add a tag to each volume you want snapshots of, configure and install a cronjob for aws-snapshot-tool and you are off. It will even handle rolling snapshots on a day, week and year so that you can setup the retention policy to suit.

Features:
- *Python based*: Leverages boto and is easy to configure and install as a crontab
- *Simple tag system*: Just add a tag to each of your EBS volumes you want snapshots of
- *Configure retention policy*: Configure how many days, weeks, and month snapshots you want to retain
- *SNS Notifications*: aws-snapshot-tool works with Amazon SNS our of the box, so you can be notified of snapshots

Usage
==========
1. Install and configure Python and Boto (See: https://github.com/boto/boto)
2. Create a SNS topic in AWS and copy the ARN into the config file
3. Subscribe with a email address to the SNS topic
4. Create a snapshot user in IAM and put the key and secret in the config file
5. Create a security policy for this user (see the iam.policy.sample)
6. Copy config.sample to config.py
7. Decide how many versions of the snapshots you want for day/week/month and change this in config.py
8. Change the Region and Endpoint for AWS in the config.py file
9. Optionally specify a proxy if you need to, otherwise set it to '' in the config.py
10. Give every Volume or Instance for which you want snapshots a Tag with a Key and a Value and put these in the config file. Default: "MakeSnapshot" and the value "True"
11. Install the script in the cron: 

		# chmod +x makesnapshots.py
		# crontab -e
		30 1 * * 1-5 /opt/aws-snapshot-tool/makesnapshots.py day
		30 2 * * 6 /opt/aws-snapshot-tool/makesnapshots.py week
		30 3 1 * * /opt/aws-snapshot-tool/makesnapshots.py month

Additional Notes
=========
The user that executes the script needs the following policies: see iam.policy.sample
