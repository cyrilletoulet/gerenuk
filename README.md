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
```sql
CREATE DATABASE gerenuk;
CREATE USER 'gerenuk'@'%' IDENTIFIED BY '*secret*';
GRANT ALL PRIVILEGES ON gerenuk.* TO 'gerenuk'@'%';
CREATE USER 'gerenuk_dashboard'@'%' IDENTIFIED BY '*secret*';
GRANT SELECT ON gerenuk.* TO 'gerenuk_dashboard'@'%';
FLUSH PRIVILEGES;

USE gerenuk;
CREATE TABLE IF NOT EXISTS instances_monitoring (
  uuid CHAR(37) PRIMARY KEY,
  hypervisor VARCHAR(127) NOT NULL,
  vcores SMALLINT UNSIGNED NOT NULL, 
  vram MEDIUMINT UNSIGNED NOT NULL,
  hourly_vcpu_usage VARCHAR(255) NOT NULL,
  daily_vcpu_usage VARCHAR(255) NOT NULL,
  weekly_vcpu_usage VARCHAR(255) NOT NULL,
  hourly_cpu_usage VARCHAR(255) NOT NULL,
  daily_cpu_usage VARCHAR(255) NOT NULL,
  weekly_cpu_usage VARCHAR(255) NOT NULL,
  hourly_mem_usage VARCHAR(255) NOT NULL,
  daily_mem_usage VARCHAR(255) NOT NULL,
  weekly_mem_usage VARCHAR(255) NOT NULL,
  deleted INT(1) NOT NULL DEFAULT 0,
  last_update DATETIME NOT NULL DEFAULT '0000-00-00 00:00:00'
);
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
systemctl stop gerenuk-*
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
[DEFAULT]
# The database hostname or IP address.
db_host = database.mydomain

# The database name.
db_name = gerenuk

# The database user.
db_user = gerenuk

# The password corresponding to database user.
db_pass = *secret*


[libvirtmon]
# The file used by libvirt monitoring daemon to save pid.
# Warning: this file has to be writable and readable by daemon user.
pid_file = /var/run/gerenuk-daemon.pid

# The instances monitoring grequency (in seconds).
monitoring_frequency = 300

# The monitoring sampling duration (in seconds).
sampling_time = 3
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
