# Gerenuk
Gerenuk is a cloud monitoring tools set.

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


## Documentation

Please let us know if you find an error or a lack in the documentation.

 * [Installation](documentation/install.md)
 * [Update](documentation/update.md)
 * [Config reference](documentation/config.md)
 * [Development guide](documentation/develop.md)


## Known limitations and issues

 * The alert for max vcpu per user in a project depends of the existence of base flavor
