# Gerenuk

A cloud monitoring tools set


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


### Cloud controller

Gerenuk needs to store collected data in a MySQL-like database.

To create the required database:
```bash
mysql -u root -h $DB_HOST -p -e "CREATE DATABASE gerenuk;"
mysql -u root -h $DB_HOST -p -e "CREATE USER 'gerenuk'@'%' IDENTIFIED BY '*secret*';"
mysql -u root -h $DB_HOST -p -e "CREATE USER 'gerenuk_dashboard'@'%' IDENTIFIED BY '*secret*';"
mysql -u root -h $DB_HOST -p -e "GRANT ALL PRIVILEGES ON gerenuk.* TO 'gerenuk'@'%';"
mysql -u root -h $DB_HOST -p -e "GRANT SELECT ON gerenuk.* TO 'gerenuk_dashboard'@'%';"
./bin/gerenuk-db-wizard
```
Please replace *secret* by suitable passwords.



### Cloud hypervisors

On libvirt hypervisors, install the following additionnal packages:
```bash
yum -y install libvirt-python
```

Install daemon:
```bash
cp bin/gerenuk-libvirtmon /usr/bin/
cp systemd/gerenuk-libvirtmon.service /usr/lib/systemd/system/
```

Configure database in **/etc/gerenuk/gerenuk.conf** (see config reference for details).

Finally, start the service:
```bash
systemctl start gerenuk-libvirtmon.service
systemctl enable gerenuk-libvirtmon.service
```


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


## Configuration

By default, gerenuk daemons will look for configuration in /etc/gerenuk/gerenuk.conf.


### Configuration reference
Instances monitoring specific settings:
```
[database]
# The database hostname or IP address.
db_host = database.mydomain

# The database name.
db_name = gerenuk

# The database user.
db_user = gerenuk

# The password corresponding to database user.
db_pass = *secret*


[keystone_authtoken]
# The complete public Identity API endpoint.
auth_url = https://controller:5000/v3

# The domain name containing project.
project_domain_name = default

# The domain name containing user.
user_domain_name = default

# The project domain name to scope to.
project_name = admin

# The username.
username = gerenuk

# The user's password.
password = *secret*


[libvirt]
# The file used by libvirt monitoring daemon to save pid.
# Warning: this file has to be writable and readable by daemon user.
pid_file = /var/run/gerenuk-libvirtmon.pid

# The instances monitoring frequency (in seconds).
monitoring_frequency = 300

# The monitoring sampling duration (in seconds).
sampling_time = 3


[openstack]
# The file used by libvirt monitoring daemon to save pid.
# Warning: this file has to be writable and readable by daemon user.
pid_file = /var/run/gerenuk-openstackmon.pid

# The project config directory
projects_dir = /etc/gerenuk/project.d/

# The openstack monitoring frequency (in seconds).
monitoring_frequency = 3600
```


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

Alerts API:
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
            print " - Message (en): " + alert["message_en"]
            print " - Message (fr): " + alert["message_fr"]
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
            print " - Message (en): " + alert["message_en"]
            print " - Message (fr): " + alert["message_fr"]
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
