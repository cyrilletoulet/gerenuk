# Gerenuk development guide
## Internal API

Instances monitoring API sample:
```python
#!/usr/bin/python3

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
#!/usr/bin/python3
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


## Environment
In order to configure a temporary development environment, you can manually specify gerenuk path: 
```bash
export PYTHONPATH="/path/to/gerenuk/usr/lib/python3/dist-packages"
export PATH="$PATH:/path/to/gerenuk/usr/bin"
```


## Build distribution tarball

To build a distribution tarball:
```bash
python setup.py sdist
```

The distribution version is set in setup.py file.
