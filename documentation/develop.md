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
        uuids = ["69243c24-d544-43c2-a7db-2608e862522a"]
        results = api.get_instances_monitoring(uuids)

        for uuid in results:
            print(uuid + ": " + str(results[uuid]))

    except gerenuk.ConfigError as e:
        print("Configuration error: %s" % str(e), file=sys.stderr)
        sys.exit(1)

    except gerenuk.DependencyError as e:
        print("Missing dependency: %s" % str(e), file=sys.stderr)
        sys.exit(1)
        
    except Exception as e:
        print("Service failure: %s" % str(e), file=sys.stderr)
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
        project = "8452fbf257b64ea7beecf4a1ce0de6c1"
        read_alerts = api.get_read_alerts(project)
        
        for alert in read_alerts:
            dest = alert["uuid"]
            if not(alert["uuid"]):
                dest = "all members of project"
            
            print("Alert #" + str(alert["id"]) + " in project " + project)
            print(" - Severity: " + SEVERITY[alert["severity"]])
            print(" - User: " + dest)
            print(" - Timestamp: " + str(alert["timestamp"]))
            print(" - Message: " + alert["message"])
            print()

        # Get unread alerts
        unread_alerts = api.get_unread_alerts(project)
        read_ids = list()

        for i in range(0, min(2, len(unread_alerts))):
            read_ids.append(unread_alerts[i]["id"])

        # Tags the two first alerts as read
        print("Alerts to tag as read: " + ", ".join([str(id) for id in read_ids]))
        api.tag_alerts_as_read(read_ids)
        print()

        # Get read alerts once again
        read_alerts = api.get_read_alerts(project)
        
        for alert in read_alerts:
            dest = alert["uuid"]
            if not(alert["uuid"]):
                dest = "all members of project"
            
            print("Alert #" + str(alert["id"]) + " in project " + project)
            print(" - Severity: " + SEVERITY[alert["severity"]])
            print(" - User: " + dest)
            print(" - Timestamp: " + str(alert["timestamp"]))
            print(" - Message: " + alert["message"])
            print()

    except gerenuk.ConfigError as e:
        print("Configuration error: %s" % str(e), file=sys.stderr)
        sys.exit(1)

    except gerenuk.DependencyError as e:
        print("Missing dependency: %s" % str(e), file=sys.stderr)
        sys.exit(1)
        
    except Exception as e:
        print("Service failure: %s" % str(e), file=sys.stderr)
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
