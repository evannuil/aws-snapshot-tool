# aws-autosnap
aws-autosnap is a python script to make it easy to *systematically snapshot any instances you wish*.

Simply add a tag to each instance you want snapshots of, configure and install a cronjob for aws-autosnap and you are off. It will even handle cleaning old snapshots on a daily, weekly, or yearly basis so that you can setup the retention policy to suit.

Features:
- *Python based*: Leverages boto and is easy to configure and schedule (e.g. with cron, jenkins, etc)
- *Tag-based configuration*: Instance/volume specific settings are set using tags directly on those objects.
- *Flexible frequency/retention policy*: Specify snapshot frequency and snapshot retention using either the config file and tags
- *SNS Notifications*: Autosnap works with Amazon SNS our of the box, so you can be notified of snapshots


## Requirements
This script currently works only in Python 2.7. Python 3.x support is under development. 

Run `pip install -r requirements.txt` in install these dependencies:

* [Boto](https://github.com/boto/boto) >= 2.38.0
* [Future](https://pypi.python.org/pypi/future) >= 0.14.3


## Usage

### Authentication
You'll need to give autosnap the correct permissions on your AWS account in order to function. You can use either an IAM user or role. Refer to the [sample IAM policy](iam.policy.sample) when making your IAM policy attached to this user/role. If you're not using SNS notifications, you can remove that portion.

* If you're using an IAM user, you must set the access and secret keys in the config file, or as [environment variables](http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html#cli-environment).
* If you're using an EC2 role, just run the script! It'll authenticate automatically (just make sure you remove the two lines in your config file that specify the keys).

### SNS (optional)
If you'd like to use SNS notifications, create an SNS topic in your AWS account and set the ARN in the config file.

### Configuration
1. First, create a `config.py` in the script's directory (use config.sample for reference).
2. For each instance that you want to snapshot, add the following tags:
  * (required) `autosnap:X`: how often (in hours) you want this instance to be snapshotted (tag name can be changed in `config.py`)
  * (optional) `autosnap_retention:X`: how many snapshots you want to keep (if not specified, it will use the value in `config.py`.
3. (optional) Tag any _volumes_ that you don't want to snapshot with `autsnap_ignore`. The tag's value doesn't matter (it can be blank).

### Scheduling (optional, but recommended)
You can schedule this script to run on a regular basis. Make sure it's set to run at least as often as the lowest value of `autosnap_frequency`. For instance, if you have some instances you want to snapshot hourly, and some you want to snapshot daily, run the script hourly, and set the `autosnap_frequency` for each instance to either 1 (for the hourlies) or 24 (for the dailies). Autosnap will only snapshot an instance if at least X hours have passed since the last snapshot it's taken (where X = `autosnap_frequency`).


### Results
When this script creates a snapshot, it will tag the snapshot with `snapshot_type:autosnap` (or whatever `tag_name` is set to in `config.py`), along with some other useful tags. Later, when it is creating the list of snapshots to delete, it will only consider snapshots for a given volume if that tag is present. This allows you to make your own snapshots without having to worry about autosnap deleting them later (just make sure you don't tag it with 'snapshot_type:autosnap').
