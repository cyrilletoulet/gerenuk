# Gerenuk changelog

## What's new in version 2.0.X?

New:
 - Code migration to python 3 (end of python2 support)
 - Add support of OpenStack Ussuri release


## What's new in version 1.4.X?

New:
 - Add an option to allow ICMP rules in default security groups
 - Alerts for max instances per user in project
 - Alerts for max vCPUs per user in project
 - Alerts for max volumes per user in project
 - Alerts for max storage per user in project
 - Auto-clean the oldest read alerts

Fixes:
 - Fix the instance migration issue in gerenuk-libvirtmon service


## What's new in version 1.3.X?

Improvments:
 - Detect and update existing unread alerts to avoid to spam users

Fixes:
 - TCP whitelist used in specific case instead of UDP whitelist


## What's new in version 1.2.X?

New:
 - Introducing log system

Improvments:
 - Retry mechanisms
 - Quality of code

Fixes:
 - Security groups alerts perimeter


## What's new in version 1.1.X?

New:
 - Introducing an openstack monitor (instances, volumes and security groups)

Improvments:
 - Configuration consistency
 - Quality of code

Fixes:
 - A typo in README

Operations:
 - Update the database
 - Move the DB configuration from ''DEFAULT'' to ''database'' group

