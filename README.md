# Gerenuk

A cloud monitoring tools set

## Features

 * Alerts for instances running since a while
 * Alerts for instances stopped since a while
 * Alerts for instances in error status
 * Alerts for max vcpu per user in a project
 * Alerts for max instances per user in a project
 * Alerts for orphan volumes (used to host a root disk and undeleted with instance)
 * Alerts for max volumes per user in a project
 * Alerts for max storage (virtual volume) per user in a project
 * Alerts for volumes unused since a while
 * Alerts for volumes in error status
 * Alerts for rules in default a security group
 * Alerts for unauthorized port in a security group
 * Alerts for ports open to the entire Internet in a security group
 * Alerts for ports widely open in a security group
 * Custom configuration per project
 * Instances whitelist
 * Volumes whitelist
 * Security groups whitelist
 * Port whitelist

### Known limitations and issues

 * The alert for max vcpu per user in a project depends of the existence of base flavor


## Releases

 * OpenStack >= Ussuri: gerenuk v2 comming soon...
 * OpenStack <= Train: gerenuk 1.4.0


## Installation
### Prerequisites

On all servers, install the required python packages: 
```bash
yum install python-pip mysql-connector-python
```

To install gerenuk lib from distribution tarball:
```bash
pip install gerenuk-x.y.z.tar.gz
```

To remove the installed gerenuk lib:
```bash
pip uninstall gerenuk
```

Create the config directory:
```bash
mkdir /etc/gerenuk
mkdir /etc/gerenuk/project.d
chmod -R 711 /etc/gerenuk
```


### Cloud controller

Gerenuk needs to store collected data in a MySQL-like database.

Configure database in **/etc/gerenuk/gerenuk.conf** (see config reference for details).

Create the required database:
```bash
mysql -u root -h $DB_HOST -p -e "CREATE DATABASE gerenuk;"
mysql -u root -h $DB_HOST -p -e "CREATE USER 'gerenuk'@'%' IDENTIFIED BY '*secret*';"
mysql -u root -h $DB_HOST -p -e "CREATE USER 'gerenuk_dashboard'@'%' IDENTIFIED BY '*secret*';"
mysql -u root -h $DB_HOST -p -e "GRANT ALL PRIVILEGES ON gerenuk.* TO 'gerenuk'@'%';"
mysql -u root -h $DB_HOST -p -e "GRANT SELECT, UPDATE ON gerenuk.* TO 'gerenuk_dashboard'@'%';"
./bin/gerenuk-db-wizard -c /etc/gerenuk/gerenuk.conf
```
Please replace *secret* by suitable passwords.


Gerenul also needs to call OpenStack APIs, especially the Keystone and Nova ones.

In **/etc/keystone/policy.json**, configure the following rules:
```json
    "project_manager": "role:project_manager",
    "identity:get_user": "rule:admin_or_owner or rule:project_manager",
```

In **/etc/nova/policy.json**, configure the following rules:
```json
    "project_manager": "role:project_manager and project_id:%(project_id)s",
    "default": "rule:admin_or_user or rule:project_manager",
    "os_compute_api:os-hypervisors": "rule:default",
```

And restart the concerned APIs:
```bash
systemctl restart openstack-nova-api.service httpd.service
```


Install daemon:
```bash
cp bin/gerenuk-openstackmon /usr/bin/
cp systemd/gerenuk-openstackmon.service /usr/lib/systemd/system/
systemctl daemon-reload
```

Finally, start the services:
```bash
systemctl start gerenuk-openstackmon.service
systemctl enable gerenuk-openstackmon.service
```

Logs are stored in **/var/log/gerenuk-openstackmon.log**.



### Cloud hypervisors

Configure database in **/etc/gerenuk/gerenuk.conf** (see config reference for details).

On libvirt hypervisors, install the following additionnal packages:
```bash
yum -y install libvirt-python
```

Install daemon:
```bash
cp bin/gerenuk-libvirtmon /usr/bin/
cp systemd/gerenuk-libvirtmon.service /usr/lib/systemd/system/
systemctl daemon-reload
```

Finally, start the service:
```bash
systemctl start gerenuk-libvirtmon.service
systemctl enable gerenuk-libvirtmon.service
```

Logs are stored in **/var/log/gerenuk-libvirtmon.log**.


## Upgrade

To update the python library, stop all the gerenuk services:
```bash
systemctl snapshot gerenuk-services
systemctl stop gerenuk-*.service
```

Upgrade gerenuk from new distribution:
```bash
pip install dist/gerenuk-x.y.z.tar.gz
```

And finally restart your services from snapshot:
```bash
systemctl isolate gerenuk-services.snapshot
systemctl delete gerenuk-services.snapshot
```

To update the database, run the DB wizard (credentials needs to be configured in **/etc/gerenuk/gerenuk.conf**):
```bash
./bin/gerenuk-db-wizard -c /etc/gerenuk/gerenuk.conf
```


## Configuration

By default, gerenuk daemons will look for configuration in /etc/gerenuk/gerenuk.conf.

Don't forget to restrict rights of each configuration file:
```bash
chmod -R 600 /etc/gerenuk/gerenuk.conf
chmod -R 600 /etc/gerenuk/project.d/*
```

### The main configuration reference

For the main configuration reference, see **doc/gerenuk.conf**.

### OpenStack project configuration reference

To monitor an OpenStack project, create a specific configuration file in /etc/gerenuk/project.d.
For more consistency, you can name your configuration files following the convention *domain.project.conf*.

For the project specific configuration reference, see **doc/project.d/project-sample.conf**.



## Development
### API

Instances monitoring API sample:
```python
#!/usr/bin/python2

import sys
import getopt
import gerenuk
import gerenuk.api

if __name__ == "__main__":
    try:
        config = gerenuk.Config()

        opts, args = getopt.getopt(sys.argv[1:], 'c:', ['config='])
        for opt, value in opts:
            if opt in ('-c', '--config'):
                config.load(value)

        api = gerenuk.api.InstancesMonitorAPI(config)
	uuids = ["64989afb-73c6-4bfe-8c0f-359c5ac55914", "d0a3ea06-92d9-422b-aaf6-f8784bf57c5d"]
        results = api.get_instances_monitoring(uuids)

	for uuid in results:
	    print uuid + ": " + str(results[uuid])

    except gerenuk.ConfigError, e:
        print >>sys.stderr, "Configuration error: %s" % str(e)
        sys.exit(1)

    except gerenuk.DependencyError, e:
        print >>sys.stderr, "Missing dependency: %s" % str(e)
        sys.exit(1)

    except Exception, e:
        print >>sys.stderr, "Service failure: %s" % str(e)
        sys.exit(1)

    finally:
        sys.exit(0)
```

Alerts API sample:
```python
#!/usr/bin/python2
# -*- coding: utf-8 -*-

import sys
import getopt
import gerenuk
import datetime
import gerenuk.api

SEVERITY = ["INFO", "ALERT", "WARNING", "CRITICAL"]

if __name__ == "__main__":
    try:
        config = gerenuk.Config()

        opts, args = getopt.getopt(sys.argv[1:], 'c:', ['config='])
        for opt, value in opts:
            if opt in ('-c', '--config'):
                config.load(value)

        api = gerenuk.api.AlertsAPI(config)

        # Get read alerts
        project = "75a5d7351c6c4a40ad9fc3ab0a50f4d0"
        read_alerts = api.get_read_alerts(project)
        
        for alert in read_alerts:
            dest = alert["uuid"]
            if not(alert["uuid"]):
                dest = "all members of project"
            
            print "Alert #" + str(alert["id"]) + " in project " + project
            print " - Severity: " + SEVERITY[alert["severity"]]
            print " - User: " + dest
            print " - Timestamp: " + str(alert["timestamp"])
            print " - Message: " + alert["message"]
            print

        # Get unread alerts
        unread_alerts = api.get_unread_alerts(project)
        read_ids = list()

        for i in range(0, min(2, len(unread_alerts))):
            read_ids.append(unread_alerts[i]["id"])

        # Tags the two first alerts as read
        print "Alerts to tag as read: " + ", ".join([str(id) for id in read_ids])
        api.tag_alerts_as_read(read_ids)
        print

        # Get read alerts once again
        read_alerts = api.get_read_alerts(project)
        
        for alert in read_alerts:
            dest = alert["uuid"]
            if not(alert["uuid"]):
                dest = "all members of project"
            
            print "Alert #" + str(alert["id"]) + " in project " + project
            print " - Severity: " + SEVERITY[alert["severity"]]
            print " - User: " + dest
            print " - Timestamp: " + str(alert["timestamp"])
            print " - Message: " + alert["message"]
            print

    except gerenuk.ConfigError, e:
        print >>sys.stderr, "Configuration error: %s" % str(e)
        sys.exit(1)

    except gerenuk.DependencyError, e:
        print >>sys.stderr, "Missing dependency: %s" % str(e)
        sys.exit(1)

    except Exception, e:
        print >>sys.stderr, "Service failure: %s" % str(e)
        sys.exit(1)

    finally:
        sys.exit(0)
```



### Environment
In order to configure a temporary development environment, you can manually specify gerenuk path: 
```bash
export PYTHONPATH="/path/to/gerenuk/usr/lib/python2/dist-packages"
export PATH="$PATH:/path/to/gerenuk/usr/bin"
```


### Build distribution tarball

To build a distribution tarball:
```bash
python setup.py sdist
```

The distribution version is set in setup.py file.
