#!/usr/bin/env python
#
# (c) 2012/2014 E.M. van Nuil / Oblivion b.v.
# Update 2015 by Zach Himsel

# Load our dependent libraries
from boto.ec2.connection import EC2Connection
from boto.ec2.regioninfo import RegionInfo
import boto.sns
from datetime import datetime
import time
import sys
import logging
from config import config
from os import environ


# Let's initialize some stuff to use later...
# Init message to return result via SNS
message = ""
errmsg = ""
# Init count variables
count_creates = 0
count_deletes = 0
count_errors = 0
count_success = 0
count_ignores = 0
count_skips = 0
count_processed = 0


# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    datefmt='%y-%m-%d %H:%M',
                    filename=config.get('log_file'),
                    filemode='a')

# Set up log stream to mirror to stdout
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

# Start log
if config.get('dry_run') is None:
    logging.info("Initializing snapshot process")
else:
    logging.info("Initializing snapshot dry run")


# Get settings from config.py
ec2_region_name = config.get('ec2_region_name')
ec2_region_endpoint = config.get('ec2_region_endpoint')
sns_arn = config.get('sns_arn')
proxyHost = config.get('proxyHost')
proxyPort = config.get('proxyPort')
tag_name = config.get('tag_name')
region = RegionInfo(name=ec2_region_name, endpoint=ec2_region_endpoint)


# Set up our AWS and SNS connection objects
try:
    # Try to load user-specified access keys (if they exist)
    try:
        # From environment variables
        aws_access_key = environ['AWS_ACCESS_KEY_ID']
        aws_secret_key = environ['AWS_SECRET_ACCESS_KEY']
    except:
        # Or from the config file (if ENV don't exist)
        aws_access_key = config.get('aws_access_key')
        aws_secret_key = config.get('aws_secret_key')
    if proxyHost:
        # Did the user specify proxy settings?
        aws = EC2Connection(aws_access_key, aws_secret_key, region=region,
                            proxy=proxyHost, proxy_port=proxyPort)
        sns = boto.sns.connect_to_region(
            ec2_region_name,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            proxy=proxyHost, proxy_port=proxyPort)
    else:
        # No?
        aws = EC2Connection(aws_access_key, aws_secret_key, region=region)
        sns = boto.sns.connect_to_region(
            ec2_region_name,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key)
    logging.info("Authenticating with IAM access key: " + aws_access_key)
except:
    # If they didn't, assume we're using an IAM role
    if proxyHost:
        # Did the user specify proxy settings?
        aws = EC2Connection(region=region, proxy=proxyHost, proxy_port=proxyPort)
        sns = boto.sns.connect_to_region(ec2_region_name, proxy=proxyHost,
                                         proxy_port=proxyPort)
    else:
        # No?
        aws = EC2Connection(region=region)
        sns = boto.sns.connect_to_region(ec2_region_name)
    logging.info("Authenticating with IAM Role")


# Define some functions
def date_compare(snapshot1, snapshot2):
    # Sort the delete list by snapshot age (oldest to newest)
    if snapshot1.start_time < snapshot2.start_time:
        return -1
    elif snapshot1.start_time == snapshot2.start_time:
        return 0
    return 1


# Check if the latest snapshot is older than our specified frequency
def frequency_check():
    snapshots = get_snapshots(volume)  # Get a list of all the snapshots for our volume
    if not snapshots:  # Snapshot if there are no existing snapshots
        return True
    else:  # If there are, check how old the last one is.
        snapshots.sort(date_compare, reverse=True)  # Order our snapshots newest to oldest
        current_time = time.mktime(time.gmtime())
        snap_time = time.mktime(time.strptime(snapshots[0].start_time, "%Y-%m-%dT%H:%M:%S.000Z"))
        # Compare with 5 minute buffer time
        if (current_time - snap_time) > ((snapshot_frequency*60*60) - 300):
            return True
        else:
            return False


def get_snapshots(volume):
    snapshots = aws.get_all_snapshots(filters={
        'volume-id': volume.id,
        'tag:snapshot_type': 'autosnap'})
    return snapshots


def create_snapshot():
    # Set the snapshot description
    description = "AUTOSNAP: {0} ({1}) at {2}".format(
        instance_name,
        volume.attach_data.device,
        datetime.today().strftime('%Y-%m-%d %H:%M:%S'))
    # Create snapshot (and store the ID)
    snapshot = volume.create_snapshot(description)
    # Add some tags to the snapshot for identification
    snapshot.add_tag("Name", instance_name)
    snapshot.add_tag("snapshot_type", tag_name)
    snapshot.add_tag("instance_id", instance.id)
    snapshot.add_tag("volume_id", volume.id)
    snapshot.add_tag("mount_point", volume.attach_data.device)
    if snapshot_frequency:
        snapshot.add_tag("snapshot_frequency", snapshot_frequency)
    else:
        snapshot.add_tag("snapshot_frequency", "null")
    return snapshot


def clean_snapshots():
    deletes = 0  # Init our local deletion counter
    deletelist = []  # Make sure the delete list is blank!

    # Make a new list of snapshots for this instance that has our tag in it
    snapshots = get_snapshots(volume)

    for snapshot in snapshots:
        deletelist.append(snapshot)
    deletelist.sort(date_compare)

    # And trim off the latest X snapshots
    delta = len(deletelist) - keep_snapshots
    for deletesnap in range(delta):
        snapshot = deletelist[deletesnap]
        logging.info("%s/%s/%s: Deleting snapshot (%s on %s)",
                     instance.id, volume.id, snapshot.id, volume.attach_data.device, instance_name)
        snapshot.delete()  # Delete it
        deletes += 1  # Increase our deletion counter
    return deletes


# Alright, let's start doing things
# First, make a list of all our instances
instances = aws.get_only_instances()

# ...and do things for each one.
for instance in instances:
    try:
        # Check if the instance has our tag, and get the frequency from it
        snapshot_frequency = int(instance.tags[tag_name])
    except:
        # If not, skip to the next instance
        continue

    try:
        # Check if the instance has a retention override tag
        keep_snapshots = int(instance.tags['autosnap_retention'])
    except:
        # Otherwise, set it to the global setting
        keep_snapshots = int(config.get('keep_snapshots'))

    try:
        # Get instance's Name tag
        instance_name = "{0}".format(instance.tags['Name'])
    except:
        # Or set it to the instance ID if it doesn't exist
        instance_name = "{0}".format(instance.id)

    # Make a list of all volumes attached to this instance
    volumes = aws.get_all_volumes(filters={
        'attachment.instance-id': instance.id})

    for volume in volumes:
        count_processed += 1  # Increase our "total processed" count

        try:
            # Ignore volumes tagged with 'autosnap_ignore' from that list
            volume.tags['autosnap_ignore']
            logging.info("%s/%s: Ignoring volume, \'autosnap_ignore\' tag present (%s on %s) ",
                         instance.id, volume.id, volume.attach_data.device, instance_name)
            count_ignores += 1  # Increase our "total ignored" counter
            continue
        except:
            pass

        try:
            if frequency_check():
                # Take snapshot if it's old enough
                if config.get('dry_run') is None:
                    snapshot = create_snapshot()  # create the snapshot!
                    logging.info("%s/%s/%s: Creating snapshot (%s on %s)",
                                 instance.id,
                                 volume.id,
                                 snapshot.id,
                                 volume.attach_data.device,
                                 instance_name)
                else:
                    # but not if we're doing a dry run
                    logging.info("%s/%s: Creating snapshot (%s on %s)",
                                 instance.id, volume.id, volume.attach_data.device, instance_name)
                count_creates += 1  # increase our total success count
            else:
                logging.info("%s/%s: Skipping volume, last snapshot not old enough (%s on %s)",
                             instance.id, volume.id, volume.attach_data.device, instance_name)
                count_skips += 1  # increase our total skip count
        except Exception as e:
            logging.info("%s/%s: Error creating snapshot for volume: %s",
                         instance.id, volume.id, e)
            count_errors += 1

        # Clean up old snapshots
        try:
            if config.get('dry_run') is None:
                count_deletes += clean_snapshots()  # Do it, and add deletes to global counter
            else:
                # but not if we're doing a dry run
                pass
        except Exception as e:
            logging.info("%s/%s: Error cleaning old snapshots for volume: %s",
                         instance.id, volume.id, e)
            count_errors += 1


# Finish up the log file...
logging.info("Finished processing snapshots")
logging.info("Volumes processed: %s", str(count_processed))
logging.info("Volumes ignored: %s", str(count_ignores))
logging.info("Volumes skipped: %s", str(count_skips))
logging.info("Snapshots created: %s", str(count_creates))
logging.info("Snapshots deleted: %s", str(count_deletes))
logging.info("Errors: %s", str(count_errors))

# Report outcome to SNS (if configured)
if sns_arn:
    if errmsg:
        sns.publish(
            sns_arn, 'Error in processing volumes: '
            + errmsg, 'Error with AWS Snapshot')
    sns.publish(sns_arn, message, 'Finished AWS snapshotting')
