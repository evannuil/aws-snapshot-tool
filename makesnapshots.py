#!/usr/bin/python
#
# (c) 2012/2013 E.M. van Nuil / Oblivion b.v.
#
# makesnapshots.py version 3.0
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
# version 1.6: Public release
# version 2.0: Added daily, weekly and montly retention
# version 3.0: Rewrote deleting functions, changed description

from boto.ec2.connection import EC2Connection
from boto.ec2.regioninfo import RegionInfo
import boto.sns
from datetime import datetime
import sys
import logging
from config import config

if (len(sys.argv) < 2):
	print('Please use the parameter day, week or month.')
	quit()
else:
	if sys.argv[1]=='day':
		run = 'day'
		date_suffix = datetime.today().strftime('%a')
	elif sys.argv[1]=='week':
		run = 'week'
		date_suffix = datetime.today().strftime('%U')
	elif sys.argv[1]=='month':
		run = 'month'
		date_suffix = datetime.today().strftime('%b')
	else:
		print('Please use the parameter day, week or month')
		quit()

# Message to return result via SNS
message = ""

# Counters
total_creates = 0
total_deletes = 0

# List with snapshots to delete
deletelist = []

# Setup the logging
logging.basicConfig(filename=config['log_file'], level=logging.INFO)
start_message = 'Start making ' + run + ' snapshots at ' + datetime.today().strftime('%d-%m-%Y %H:%M:%S')
message += start_message + "\n" + "\n"
logging.info(start_message)

# Get settings from config.py
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
keep_week = config['keep_week']
keep_day = config['keep_day']
keep_month = config['keep_month']
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
if proxyHost == '':
	# non proxy:
	sns = boto.connect_sns(aws_access_key,aws_secret_key,region=sns_region)
else:
	# proxy:
	sns = boto.connect_sns(aws_access_key,aws_secret_key,region=sns_region,proxy=proxyHost, proxy_port=proxyPort)


vols = conn.get_all_volumes(filters={config['tag_name']: config['tag_value']})
for vol in vols:
	message += "\n"
	try:
		count_total += 1		
		logging.info(vol)
		print vol
		description = run + '_snapshot ' + vol.id + '_' + run + '_' + date_suffix + ' by snapshot script at ' + datetime.today().strftime('%d-%m-%Y %H:%M:%S')
		if vol.create_snapshot(description):
			suc_message = 'Snapshot created with description: ' + description
			print suc_message
			logging.info(suc_message)
			total_creates += 1
		snapshots = vol.snapshots()
		for snap in snapshots:
			sndesc = snap.description
			if (sndesc.startswith('week_snapshot') and run == 'week'):
				deletelist.append(snap)
			elif (sndesc.startswith('day_snapshot') and run == 'day'):
				deletelist.append(snap)
			elif (sndesc.startswith('month_snapshot') and run == 'month'):
				deletelist.append(snap)
			else:
				print 'Skipping, not added to deletelist: ' + sndesc
		for snap in deletelist:
			logging.info(snap)
			logging.info(snap.start_time)
			print snap.description

		def date_compare(snap1, snap2):
			if snap1.start_time < snap2.start_time:
				return -1
			elif snap1.start_time == snap2.start_time:
				return 0
			return 1

		deletelist.sort(date_compare)
		if run=='day':
			keep = keep_day
		elif run=='week':
			keep = keep_week
		elif run=='month':
			keep = keep_month
		delta = len(deletelist) - keep
		for i in range(delta):
			del_message = 'Deleting snapshot ' + deletelist[i].description
			logging.info(del_message)
			deletelist[i].delete()
			total_deletes += 1
	except:
		print("Unexpected error:", sys.exc_info()[0])
		logging.error('Error in processing volume with id: ' + vol.id)
		sns.publish(arn,'Error in processing volume with id: ' + vol.id,'Error with AWS Snapshot')
	else:
		count_succes +=1

result= '\nFinished making snapshots at ' + datetime.today().strftime('%d-%m-%Y %H:%M:%S') + ' with ' + str(count_succes) + ' snapshots of ' + str(count_total) + ' possible.'
message += "\n" + "\n" + result
message += "\nTotal snapshots created: " + str(total_creates)
message += "\nTotal snapshots deleted: " + str(total_deletes) + "\n"
print result
sns.publish(arn,message,'Finished AWS snapshotting')
logging.info(result)