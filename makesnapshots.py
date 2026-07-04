#!/usr/bin/env python3
#
# (c) 2012/2014 E.M. van Nuil / Oblivion b.v.
#
# makesnapshots.py version 4.0
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
# version 3.1: Fix a bug with the deletelist and added a pause in the volume loop
# version 3.2: Tags of the volume are placed on the new snapshot
# version 3.3: Merged IAM role addidtion from Github
# version 4.0: Rewritten for Python 3 and boto3; adaptive API retries instead
#              of fixed sleeps; snapshot tags applied atomically at creation;
#              accurate success/error counters; non-zero exit code on errors

import argparse
import logging
import sys
from datetime import datetime

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

from config import config

DATE_SUFFIX_FORMATS = {'day': '%a', 'week': '%U', 'month': '%b'}


def parse_args():
    parser = argparse.ArgumentParser(
        description='Create EBS snapshots for tagged volumes and rotate old '
                    'snapshots on a day/week/month retention schedule.')
    parser.add_argument('period', choices=sorted(DATE_SUFFIX_FORMATS),
                        help='retention bucket this run belongs to')
    return parser.parse_args()


def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[logging.FileHandler(log_file),
                  logging.StreamHandler(sys.stdout)])
    return logging.getLogger('makesnapshots')


def build_clients(cfg):
    # Adaptive retry mode backs off automatically on EC2 API throttling,
    # replacing the fixed per-volume sleep of older versions.
    boto_config = BotoConfig(retries={'max_attempts': 10, 'mode': 'adaptive'})
    proxy_host = cfg.get('proxyHost')
    if proxy_host:
        proxy = '{}:{}'.format(proxy_host, cfg.get('proxyPort', '8080'))
        boto_config = boto_config.merge(
            BotoConfig(proxies={'http': proxy, 'https': proxy}))

    session_kwargs = {'region_name': cfg['ec2_region_name']}
    # Explicit keys in config.py take precedence; otherwise boto3 falls back
    # to its default chain (environment variables, ~/.aws, or an IAM role).
    if cfg.get('aws_access_key'):
        session_kwargs['aws_access_key_id'] = cfg['aws_access_key']
        session_kwargs['aws_secret_access_key'] = cfg['aws_secret_key']
    session = boto3.session.Session(**session_kwargs)

    ec2 = session.client('ec2', config=boto_config)
    sns = session.client('sns', config=boto_config) if cfg.get('arn') else None
    return ec2, sns


def tagged_volumes(ec2, tag_name, tag_value):
    # Older config samples included the 'tag:' filter prefix in tag_name;
    # strip it so both styles work.
    if tag_name.startswith('tag:'):
        tag_name = tag_name[len('tag:'):]
    paginator = ec2.get_paginator('describe_volumes')
    pages = paginator.paginate(
        Filters=[{'Name': 'tag:' + tag_name, 'Values': [tag_value]}])
    for page in pages:
        yield from page['Volumes']


def snapshot_tags(volume):
    # Tags starting with 'aws:' are reserved for internal use
    return [tag for tag in volume.get('Tags', [])
            if not tag['Key'].startswith('aws:')]


def create_snapshot(ec2, volume, period, date_suffix, log):
    vol_id = volume['VolumeId']
    description = '{period}_snapshot {vol}_{period}_{suffix} by snapshot script at {now}'.format(
        period=period, vol=vol_id, suffix=date_suffix,
        now=datetime.now().strftime('%d-%m-%Y %H:%M:%S'))
    kwargs = {'VolumeId': vol_id, 'Description': description}
    tags = snapshot_tags(volume)
    if tags:
        kwargs['TagSpecifications'] = [{'ResourceType': 'snapshot',
                                        'Tags': tags}]
    ec2.create_snapshot(**kwargs)
    log.info('Snapshot created with description: %s and tags: %s',
             description, tags)


def rotate_snapshots(ec2, vol_id, period, keep, log):
    snapshots = []
    paginator = ec2.get_paginator('describe_snapshots')
    pages = paginator.paginate(
        OwnerIds=['self'],
        Filters=[{'Name': 'volume-id', 'Values': [vol_id]}])
    for page in pages:
        snapshots.extend(page['Snapshots'])

    prefix = period + '_snapshot'
    candidates = sorted(
        (snap for snap in snapshots if snap['Description'].startswith(prefix)),
        key=lambda snap: snap['StartTime'])

    deleted = 0
    for snap in candidates[:max(len(candidates) - keep, 0)]:
        log.info('Deleting snapshot %s (%s)',
                 snap['SnapshotId'], snap['Description'])
        ec2.delete_snapshot(SnapshotId=snap['SnapshotId'])
        deleted += 1
    return deleted


def main():
    args = parse_args()
    period = args.period
    date_suffix = datetime.today().strftime(DATE_SUFFIX_FORMATS[period])
    keep = config.get('keep_' + period, 5)

    log = setup_logging(config.get('log_file', '/tmp/makesnapshots.log'))

    message = 'Started taking {} snapshots at {}\n\n'.format(
        period, datetime.now().strftime('%d-%m-%Y %H:%M:%S'))
    log.info(message.strip())

    ec2, sns = build_clients(config)

    total_creates = 0
    total_deletes = 0
    count_errors = 0
    count_success = 0
    count_total = 0
    errmsg = ''

    log.info('Finding volumes with tag %s=%s',
             config['tag_name'], config['tag_value'])
    for volume in tagged_volumes(ec2, config['tag_name'], config['tag_value']):
        vol_id = volume['VolumeId']
        count_total += 1
        try:
            create_snapshot(ec2, volume, period, date_suffix, log)
            total_creates += 1
            total_deletes += rotate_snapshots(ec2, vol_id, period, keep, log)
        except (BotoCoreError, ClientError) as exc:
            log.error('Error in processing volume with id %s: %s', vol_id, exc)
            errmsg += 'Error in processing volume with id: {}\n'.format(vol_id)
            count_errors += 1
        else:
            count_success += 1

    result = ('\nFinished making snapshots at {} with {} snapshots of {} '
              'possible.\n\n'.format(
                  datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
                  count_success, count_total))
    message += result
    message += '\nTotal snapshots created: {}'.format(total_creates)
    message += '\nTotal snapshots errors: {}'.format(count_errors)
    message += '\nTotal snapshots deleted: {}\n'.format(total_deletes)

    log.info(result.strip())

    if sns:
        if errmsg:
            sns.publish(TopicArn=config['arn'],
                        Subject='Error with AWS Snapshot',
                        Message='Error in processing volumes:\n' + errmsg)
        sns.publish(TopicArn=config['arn'],
                    Subject='Finished AWS snapshotting',
                    Message=message)

    return 1 if count_errors else 0


if __name__ == '__main__':
    sys.exit(main())
