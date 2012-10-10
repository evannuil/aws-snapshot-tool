#!/usr/bin/python
#
# (c) 2012 E.M. van Nuil / Oblivion b.v.
#
# makesnapshots.py version 1.5.1
#
# Changelog
# version 1:   Initial version
# version 1.1: Added description and region
# version 1.2: Added extra error handeling and logging
# version 1.3: Added SNS email functionality for succes and error reporting
# version 1.3.1: Fixed the SNS and IAM problem
# version 1.4: Moved all settings to config file
# version 1.5: Select volumes for snapshotting depending on Tag and not from config file
# version 1.5.1: Added proxyHost and proxyPort to config and connect
#
# Change the logging filename for the location of the logfile
# Change aws_access_key and aws_secret_key for the owner of the volumes
# Change the path to the volumes.cfg to include complete path (for running from cron)
#

from boto.ec2.connection import EC2Connection
from boto.ec2.regioninfo import RegionInfo
import boto.sns
from datetime import datetime
import sys
import logging
from config import config

# Message to return result via SNS
message = ""

# Setup the logging
logging.basicConfig(filename=config['log_file'], level=logging.INFO)
start_message = 'Start making snapshots at ' + datetime.today().isoformat(' ')
message += start_message + "\n" + "\n"
logging.info(start_message)

# Substitute your access key and secret key here
aws_access_key = config['aws_access_key']
aws_secret_key = config['aws_secret_key']
ec2_region_name = config['ec2_region_name']
ec2_region_endpoint = config['ec2_region_endpoint']
sns_region = boto.sns.get_region(ec2_region_name)
arn= config['arn']
proxyHost = config['proxyHost']
proxyPort = config['proxyPort']

region = RegionInfo(name=ec2_region_name, endpoint=ec2_region_endpoint)

# Number of snapshots to keep
keep = config['keep']
count_succes = 0
count_total = 0

# Connect to AWS using the credentials provided above or in Environment vars.
if proxyHost == '':
	# non proxy:
	conn = EC2Connection(aws_access_key,aws_secret_key,region=region)
else:
	# proxy:
	conn = EC2Connection(aws_access_key,aws_secret_key,region=region,proxy=proxyHost, proxy_port=proxyPort)

# Connect to SNS
# non proxy:
# sns = boto.connect_sns(aws_access_key,aws_secret_key,region=sns_region)
# proxy:
sns = boto.connect_sns(aws_access_key,aws_secret_key,region=sns_region,proxy=proxyHost, proxy_port=proxyPort)


vols = conn.get_all_volumes(filters={config['tag_name']: config['tag_value']})
for vol in vols:
	message += "\n"
	try:
		count_total += 1		
		logging.info(vol)
		description = 'Snapshot ' + vol.id + ' by snapshot script at ' + datetime.today().isoformat(' ')
		if vol.create_snapshot(description):
			suc_message = 'Snapshot created with description: ' + description
			message += suc_message + "\n"
			logging.info(suc_message)
		snapshots = vol.snapshots()
		snapshot = snapshots[0]
		for snap in snapshots:
			logging.info(snap)
		def date_compare(snap1, snap2):
			if snap1.start_time < snap2.start_time:
				return -1
			elif snap1.start_time == snap2.start_time:
				return 0
			return 1
		snapshots.sort(date_compare)
		delta = len(snapshots) - keep
		for i in range(delta):
			del_message = 'Deleting snapshot ' + snapshots[i].description
			message += del_message + "\n"
			logging.info(del_message)
			if snapshots[i].description.startswith('Created by CreateImage'):
				print("Skip")
			else:
				snapshots[i].delete()
	except:
		print("Unexpected error:", sys.exc_info()[0])
		logging.error('Error in processing volume with id: ' + vol.id)
		sns.publish(arn,'Error in processing volume with id: ' + vol.id,'Error with AWS Snapshot')
	else:
		count_succes +=1

result= 'Finished making snapshots at ' + datetime.today().isoformat(' ') + ' with ' + str(count_succes) + ' snapshots of ' + str(count_total) + ' possible.'
message += "\n" + "\n" + result
print result
sns.publish(arn,message,'Finished AWS snapshotting')
logging.info(result)