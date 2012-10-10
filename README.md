aws-snapshot-tool
=================

A Python/Boto script that automates snapshot making of EBS volumes and rotating.

AWS Backuptool

This python scripts makes a snapshot of every volume which has a specific TAG which is defined in the config file. It keeps the 5 (configurable) most current versions of the snapshots.

The access_key and secret_key can be provided as environment vars or put in the config.

For the SNS functionality there must be a topic and the ARN of the topic must be in the config.


The user that executes the script needs the following policies:


 {
   "Statement": [
   {
 	  "Sid": "Stmt1343909064218",
 	  "Action": [
 		"sns:Publish"
 	  ],
 	  "Effect": "Allow",
 	  "Resource": [
 		"arn:aws:sns:eu-west-1:xxxxxxxxx:yyyyyyy"
 	  ]
 	}
   ]
 }

 {
   "Statement": [
 	{
 	  "Sid": "Stmt1343913145933",
 	  "Action": [
 		"ec2:CreateSnapshot",
 		"ec2:CreateTags",
 		"ec2:DeleteSnapshot",
 		"ec2:DescribeAvailabilityZones",
 		"ec2:DescribeSnapshots",
 		"ec2:DescribeTags",
 		"ec2:DescribeVolumeAttribute",
 		"ec2:DescribeVolumeStatus",
 		"ec2:DescribeVolumes"
 	  ],
 	  "Effect": "Allow",
 	  "Resource": [
 		"*"
 	  ]
 	}
   ]
 }