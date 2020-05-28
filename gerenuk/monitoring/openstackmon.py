#!/usr/bin/python2
#
# This file is part of Gerenuk.
#
# Gerenuk is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# Gerenuk is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gerenuk. If not, see <https://www.gnu.org/licenses/>.
#
#
# Cyrille TOULET <cyrille.toulet@univ-lille.fr>
# Thu 28 May 10:25:09 CEST 2020

NOVA_API_VERSION = 2
CINDER_API_VERSION = 3

SEVERITY_INFO = 0
SEVERITY_ALERT = 1
SEVERITY_WARNING = 2
SEVERITY_CRITICAL = 3


from netaddr import *
import datetime
import gerenuk
import logging
import time
import sys
import os
import re



class OpenstackMonitor():
    """
    This class is used to monitor OpenStack.
    """

    def __init__(self, config):
        """
        Initialize OpenstackMonitor object.

        :param config: (gerenuk.Config) The gerenuk configuration
        """
        # Config
        self.config = config

        # Logging
        self.log = logging.getLogger("gerenuk-openstackmon")
        stderr_handler = logging.StreamHandler(sys.stderr)
        log_file_handler = logging.FileHandler(self.config.get("openstack", "log_file"))
        log_file_format = logging.Formatter('%(asctime)s [%(levelname)s] %(process)d: %(message)s')
        
        log_level = self.config.get("openstack", "log_level")
        if log_level in self.config.LOG_LEVEL_MAPPING:
            self.log.setLevel(self.config.LOG_LEVEL_MAPPING[log_level])
            log_file_handler.setLevel(self.config.LOG_LEVEL_MAPPING[log_level])
        stderr_handler.setLevel(logging.WARNING)

        log_file_handler.setFormatter(log_file_format)
        self.log.addHandler(log_file_handler)
        self.log.addHandler(stderr_handler)

        # Dependencies
        try:
            import mysql.connector
        except Exception, e:
            raise gerenuk.DependencyError(e)

        self.log.debug("gerenuk.monitoring dependencies successfully loaded")

        # MySQL
        self.log.debug("Connecting to database...")
        self.db_connect()
        self.log.debug("Connection with database successfully established")



    def __str__(self):
        """
        Give a string representation of current object.

        :return: (str) The UTF-8 encoded string representation of current object
        """
        return unicode(self).encode('utf-8')


    
    def __unicode__(self):
        """
        Give an unicode representation of current object.

        :return: (str) The unicode representation of current object
        """
        desc  = u"OpenStack monitor object\n"
        return desc


    
    def db_connect(self):
        """
        Try to connect to the database
        :raise: (gerenuk.DependencyError) When a required dependency is missing
        """
        # Dependencies
        try:
            import mysql.connector
        except Exception, e:
            raise gerenuk.DependencyError(e)

        self.database = mysql.connector.connect(
            host=self.config.get("database", "db_host"),
            user=self.config.get("database", "db_user"),
            password=self.config.get("database", "db_pass"),
            database=self.config.get("database", "db_name"),
            connection_timeout=self.config.get_int("database", "db_timeout")
        )
        self.db_cursor = self.database.cursor()

    

    def monitor_projects(self):
        """
        Browse all monitored projects from config files.
        """
        projects_dir = self.config.get("openstack", "projects_dir")
        projects = os.listdir(projects_dir)

        for project in projects:
            if not(project[-5:] == ".conf"):
                continue

            self.log.debug("Loading configuration for project %s..." % project)
            project_config = gerenuk.Config()
            project_config_file = projects_dir + "/" + project
            project_config.load(project_config_file)
            self.log.debug("Configuration file %s successfully loaded" % project_config_file)

            self.log.info("Monitoring project %s..." % project)
            self.monitor_project(project_config)
            self.log.debug("Project %s successfully monitored" % project)


    def monitor_project(self, project_config):
        """
        Monitor an openstack project.

        :param project_config: (gerenuk.Config) The project configuration
        :raise: (gerenuk.DependencyError) When a required dependency is missing
        :raise: (gerenuk.MonitoringError) When an internal error occurs
        """
        # Dependencies
        try:
            import keystoneauth1.session as keystone_session
            import keystoneauth1.identity as keystone_identity
            import keystoneclient.client as keystone_client
            import novaclient.client as nova_client
            import cinderclient.client as cinder_client
            import neutronclient.v2_0.client as neutron_client
        except Exception, e:
            raise gerenuk.DependencyError(e)

        credentials = dict()
        credentials["auth_url"] = project_config.get("keystone_authtoken", "auth_url")
        credentials["project_domain_name"] = project_config.get("keystone_authtoken", "project_domain_name")
        credentials["user_domain_name"] = project_config.get("keystone_authtoken", "user_domain_name")
        credentials["project_name"] = project_config.get("keystone_authtoken", "project_name")
        credentials["username"] = project_config.get("keystone_authtoken", "username")
        credentials["password"] = project_config.get("keystone_authtoken", "password")

        self.log.debug("Instantiating OpenStack APIs...")
        auth = keystone_identity.v3.Password(**credentials)
        session = keystone_session.Session(auth=auth)
        keystone = keystone_client.Client(session=session)
        nova = nova_client.Client(NOVA_API_VERSION, session=session)
        cinder = cinder_client.Client(CINDER_API_VERSION, session=session)
        neutron = neutron_client.Client(session=session)
        self.log.debug("OpenStack APIs successfully instantiated")

        now = datetime.date.today()
        timestamp = datetime.datetime.now()

        try:
            # Project
            project_id = ""
            for project in keystone.projects.list():
                if credentials["project_name"] == project.name:
                    project_id = project.id

            # Unread alerts
            sql = 'SELECT id, uuid, message FROM user_alerts WHERE status=1 AND project="%s";'
            self.db_cursor.execute(sql % (project_id,))
            unread_alerts = self.db_cursor.fetchall()


            # Instances
            self.log.debug("Begining of instances monitoring...")
            for instance in nova.servers.list():
                whitelist = project_config.get_list('instances', 'whitelist')
                if instance.id in whitelist:
                    continue
                
                date_format = "%Y-%m-%dT%H:%M:%SZ"
                created_at = datetime.datetime.strptime(instance.created, date_format)
                updated_at = datetime.datetime.strptime(instance.updated, date_format)
                created_delta = (now - created_at.date()).days
                updated_delta = (now - updated_at.date()).days

                created_delta_s = 's'
                if created_delta < 2:
                    created_delta_s = ''
                updated_delta_s = 's'
                if updated_delta < 2:
                    updated_delta_s = ''

                if instance.status.upper() == "ERROR":
                    self.log.debug("Found instance %s in ERROR status" % instance.id)

                    # Look for matching unread alert
                    matching_alert = None
                    regex = re.compile("^Instance %s ([\(])?.*[\)\s]?created on [0-9]{2}/[0-9]{2}/[0-9]{4} \([0-9]+ day[s]? ago\) in error \(ERROR\) since [0-9]+ day[s]?\.$" % instance.id)
                        
                    for alert in unread_alerts:
                        (id, user_id, message) = alert
                        if regex.match(message) and user_id == instance.user_id:
                            matching_alert = alert
                            break
                            
                    # Define alert message
                    message = "Instance " + instance.id
                    if instance.name:
                        message += " (" + instance.name + ")"
                    message += " created on " + created_at.strftime("%d/%m/%Y") + " (" + str(created_delta) + " day" + created_delta_s + " ago) in error ("
                    message += "ERROR) since " + str(updated_delta) + " day" + updated_delta_s + '.'

                    # Update or keep unchanged existing alerts
                    if matching_alert:
                        if matching_alert[2] != message:
                            self.log.info("The instance %s has matching unread alert in database. Updating old messages..." % instance.id)
                            sql = 'UPDATE user_alerts SET message="%s", timestamp="%s" WHERE id="%d";'
                            self.db_cursor.execute(sql % (message, timestamp, matching_alert[0]))
                            continue

                        self.log.debug("The instance %s has matching unread alert in database. Up to date" % instance.id)
                        continue

                    # Create new alert
                    self.log.info("Create alert for instance %s (in error)" % instance.id)
                    sql = 'INSERT INTO user_alerts(uuid, project, severity, message, timestamp) VALUES("%s", "%s", "%d", "%s", "%s");'
                    self.db_cursor.execute(sql % (instance.user_id, instance.tenant_id, SEVERITY_WARNING, message, timestamp))
                
                elif instance.status.upper() == "SHUTOFF":
                    if updated_delta >= project_config.get_int('instances', 'stopped_alert_delay'):
                        self.log.debug("Found instance %s in SHUTOFF status since a while" % instance.id)

                        # Look for matching unread alert
                        matching_alert = None
                        regex = re.compile("^Instance %s ([\(])?.*[\)\s]?created on [0-9]{2}/[0-9]{2}/[0-9]{4} \([0-9]+ day[s]? ago\) stopped \(SHUTOFF\) since [0-9]+ day[s]?\.$" % instance.id)
                        
                        for alert in unread_alerts:
                            (id, user_id, message) = alert
                            if regex.match(message) and user_id == instance.user_id:
                                matching_alert = alert
                                break
                            
                        # Define alert message
                        message = "Instance " + instance.id
                        if instance.name:
                            message += " (" + instance.name + ")"
                        message += " created on " + created_at.strftime("%d/%m/%Y") + " (" + str(created_delta) + " day" + created_delta_s + " ago) stopped ("
                        message += "SHUTOFF) since " + str(updated_delta) + " day" + updated_delta_s + '.'

                        # Update or keep unchanged existing alerts
                        if matching_alert:
                            if matching_alert[2] != message:
                                self.log.info("The instance %s has matching unread alert in database. Updating old messages..." % instance.id)
                                sql = 'UPDATE user_alerts SET message="%s", timestamp="%s" WHERE id="%d";'
                                self.db_cursor.execute(sql % (message, timestamp, matching_alert[0]))
                                continue

                            self.log.debug("The instance %s has matching unread alert in database. Up to date" % instance.id)
                            continue

                        # Create new alert
                        self.log.info("Create alert for instance %s (stopped since a while)" % instance.id)
                        sql = 'INSERT INTO user_alerts(uuid, project, severity, message, timestamp) VALUES("%s", "%s", "%d", "%s", "%s");'
                        self.db_cursor.execute(sql % (instance.user_id, instance.tenant_id, SEVERITY_ALERT, message, timestamp))
                
                elif instance.status.upper() == "ACTIVE":
                    if updated_delta >= project_config.get_int('instances', 'running_alert_delay'):
                        self.log.debug("Found instance %s in ACTIVE status since a while" % instance.id)

                        # Look for matching unread alert
                        matching_alert = None
                        regex = re.compile("^Instance %s ([\(])?.*[\)\s]?created on [0-9]{2}/[0-9]{2}/[0-9]{4} \([0-9]+ day[s]? ago\) running \(ACTIVE\) since a long time \([0-9]+ day[s]?\)\.$" % instance.id)
                        
                        for alert in unread_alerts:
                            (id, user_id, message) = alert
                            if regex.match(message) and user_id == instance.user_id:
                                matching_alert = alert
                                break
                            
                        # Define alert message
                        message = "Instance " + instance.id
                        if instance.name:
                            message += " (" + instance.name + ")"
                        message += " created on " + created_at.strftime("%d/%m/%Y") + " (" + str(created_delta) + " day" + created_delta_s + " ago) running ("
                        message += "ACTIVE) since a long time (" + str(updated_delta) + " day" + updated_delta_s + ")."

                        # Update or keep unchanged existing alerts
                        if matching_alert:
                            if matching_alert[2] != message:
                                self.log.info("The instance %s has matching unread alert in database. Updating old messages..." % instance.id)
                                sql = 'UPDATE user_alerts SET message="%s", timestamp="%s" WHERE id="%d";'
                                self.db_cursor.execute(sql % (message, timestamp, matching_alert[0]))
                                continue

                            self.log.debug("The instance %s has matching unread alert in database. Up to date" % instance.id)
                            continue

                        # Create new alert
                        self.log.info("Create alert for instance %s (active since a while)" % instance.id)
                        sql = 'INSERT INTO user_alerts(uuid, project, severity, message, timestamp) VALUES("%s", "%s", "%d", "%s", "%s");'
                        self.db_cursor.execute(sql % (instance.user_id, instance.tenant_id, SEVERITY_INFO, message, timestamp))


            # Volumes
            self.log.debug("Begining of volumes monitoring...")
            for volume in cinder.volumes.list():
                whitelist = project_config.get_list('volumes', 'whitelist')
                if volume.id in whitelist:
                    continue
                
                date_format = "%Y-%m-%dT%H:%M:%S.%f"
                created_at = datetime.datetime.strptime(volume.created_at, date_format)
                updated_at = datetime.datetime.strptime(volume.updated_at, date_format)
                created_delta = (now - created_at.date()).days
                updated_delta = (now - updated_at.date()).days

                created_delta_s = 's'
                if created_delta < 2:
                    created_delta_s = ''
                updated_delta_s = 's'
                if updated_delta < 2:
                    updated_delta_s = ''

                if volume.status.upper() in ("ERROR", "ERROR_DELETING"):
                    self.log.debug("Found volume %s in %s status" % (volume.id, volume.status.upper()))

                    # Look for matching unread alert
                    matching_alert = None
                    regex = re.compile("^Volume %s ([\(])?.*[\)\s]?created on [0-9]{2}/[0-9]{2}/[0-9]{4} \([0-9]+ day[s]? ago\) in error \(ERROR|ERROR_DELETING\) since [0-9]+ day[s]?\.$" % volume.id)
                        
                    for alert in unread_alerts:
                        (id, user_id, message) = alert
                        if regex.match(message) and user_id == volume.user_id:
                            matching_alert = alert
                            break
                            
                    # Define alert message
                    message = "Volume " + volume.id
                    if volume.name:
                        message += " (" + volume.name + ")"
                    message += " created on " + created_at.strftime("%d/%m/%Y") + " (" + str(created_delta) + " day" + created_delta_s + "  ago) in error ("
                    message += volume.status.upper() + ") since " + str(updated_delta) + " day" + updated_delta_s + '.'

                    # Update or keep unchanged existing alerts
                    if matching_alert:
                        if matching_alert[2] != message:
                            self.log.info("The volume %s has matching unread alert in database. Updating old messages..." % volume.id)
                            sql = 'UPDATE user_alerts SET message="%s", timestamp="%s" WHERE id="%d";'
                            self.db_cursor.execute(sql % (message, timestamp, matching_alert[0]))
                            continue

                        self.log.debug("The volume %s has matching unread alert in database. Up to date" % volume.id)
                        continue

                    # Create new alert
                    self.log.info("Create alert for volume %s (in error)" % volume.id)
                    sql = 'INSERT INTO user_alerts(uuid, project, severity, message, timestamp) VALUES("%s", "%s", "%d", "%s", "%s");'
                    self.db_cursor.execute(sql % (volume.user_id, getattr(volume, "os-vol-tenant-attr:tenant_id"), SEVERITY_WARNING, message, timestamp))

                elif volume.status.upper() == "AVAILABLE":
                    if not(volume.bootable) and not(volume.name):
                        if updated_delta >= project_config.get_int('volumes', 'orphan_alert_delay'):
                            self.log.debug("Found probably orphan volume %s" % volume.id)

                            # Look for matching unread alert
                            matching_alert = None
                            regex = re.compile("^Volume %s created on [0-9]{2}/[0-9]{2}/[0-9]{4} \([0-9]+ day[s]? ago\) probably orphan \(AVAILABLE\) since [0-9]+ day[s]?\.$" % volume.id)
                        
                            for alert in unread_alerts:
                                (id, user_id, message) = alert
                                if regex.match(message) and user_id == volume.user_id:
                                    matching_alert = alert
                                    break
                            
                            # Define alert message
                            message = "Volume " + volume.id
                            message += " created on " + created_at.strftime("%d/%m/%Y") + " (" + str(created_delta) + " day" + created_delta_s + " ago) probably orphan ("
                            message += "AVAILABLE) since " + str(updated_delta) + " day" + updated_delta_s + '.'

                            # Update or keep unchanged existing alerts
                            if matching_alert:
                                if matching_alert[2] != message:
                                    self.log.info("The volume %s has matching unread alert in database. Updating old messages..." % volume.id)
                                    sql = 'UPDATE user_alerts SET message="%s", timestamp="%s" WHERE id="%d";'
                                    self.db_cursor.execute(sql % (message, timestamp, matching_alert[0]))
                                    continue

                                self.log.debug("The volume %s has matching unread alert in database. Up to date" % volume.id)
                                continue

                            # Create new alert
                            self.log.info("Create alert for volume %s (probably orphan)" % volume.id)
                            sql = 'INSERT INTO user_alerts(uuid, project, severity, message, timestamp) VALUES("%s", "%s", "%d", "%s", "%s");'
                            self.db_cursor.execute(sql % (volume.user_id, getattr(volume, "os-vol-tenant-attr:tenant_id"), SEVERITY_ALERT, message, timestamp))
                            
                    else:
                        if updated_delta >= project_config.get_int('volumes', 'inactive_alert_delay'):
                            self.log.debug("Found volume %s inactive since a while" % volume.id)

                            # Look for matching unread alert
                            matching_alert = None
                            regex = re.compile("^Volume %s ([\(])?.*[\)\s]?created on [0-9]{2}/[0-9]{2}/[0-9]{4} \([0-9]+ day[s]? ago\) inactive \(AVAILABLE\) since [0-9]+ day[s]?\.$" % volume.id)
                        
                            for alert in unread_alerts:
                                (id, user_id, message) = alert
                                if regex.match(message) and user_id == volume.user_id:
                                    matching_alert = alert
                                    break
                            
                            # Define alert messages
                            message = "Volume " + volume.id
                            if volume.name:
                                message += " (" + volume.name + ")"
                            message += " created on " + created_at.strftime("%d/%m/%Y") + " (" + str(created_delta) + " day" + created_delta_s + " ago) inactive ("
                            message += volume.status.upper() + ") since " + str(updated_delta) + " day" + updated_delta_s + '.'

                            # Update or keep unchanged existing alerts
                            if matching_alert:
                                if matching_alert[2] != message:
                                    self.log.info("The volume %s has matching unread alert in database. Updating old messages..." % volume.id)
                                    sql = 'UPDATE user_alerts SET message="%s", timestamp="%s" WHERE id="%d";'
                                    self.db_cursor.execute(sql % (message, timestamp, matching_alert[0]))
                                    continue

                                self.log.debug("The volume %s has matching unread alert in database. Up to date" % volume.id)
                                continue

                            # Create new alert
                            self.log.info("Create alert for volume %s (inactive since a while)" % volume.id)
                            sql = 'INSERT INTO user_alerts(uuid, project, severity, message, timestamp) VALUES("%s", "%s", "%d", "%s", "%s");'
                            self.db_cursor.execute(sql % (volume.user_id, getattr(volume, "os-vol-tenant-attr:tenant_id"), SEVERITY_ALERT, message, timestamp))


            # Security Groups
            self.log.debug("Begining of security groupes monitoring...")
            for sg in neutron.list_security_groups()['security_groups']:
                if sg["project_id"] != project_id:
                    continue
                
                trusted_subnets = project_config.get_list('networks', 'trusted_subnets')
                tcp_whitelist = project_config.get_list('networks', 'tcp_whitelist')
                udp_whitelist = project_config.get_list('networks', 'udp_whitelist')

                if not("security_group_rules" in sg):
                    continue
                
                for rule in sg["security_group_rules"]:
                    date_format = "%Y-%m-%dT%H:%M:%SZ"
                    created_at = datetime.datetime.strptime(rule["created_at"], date_format)
                    created_delta = (now - created_at.date()).days
                            
                    created_delta_s = 's'
                    if created_delta < 2:
                        created_delta_s = ''
                    
                    if rule["direction"] == "egress":
                        continue
                    
                    if not (rule["remote_ip_prefix"]):
                        continue

                    if sg["name"] == "default":
                        if rule['remote_ip_prefix'] and rule['protocol'] != "icmp":
                            self.log.debug("Found user defined rule in default security group")

                            # Look for matching unread alert
                            regex = re.compile("^User defined rules in default security group \(reminder\: it's forbidden\)\!$")
                            for alert in unread_alerts:
                                (id, user_id, message) = alert
                                if regex.match(message):
                                    matching_alert = alert
                                    break
                                
                            # Define alert message
                            message = "User defined rules in default security group (reminder: it's forbidden)!"

                            # Update or keep unchanged existing alerts
                            if matching_alert:
                                self.log.debug("The default security group has matching unread alert in database. Up to date")
                                continue

                            # Create new alert
                            self.log.info("Create alert for default security group (user defined rule)")
                            sql = 'INSERT INTO user_alerts(project, severity, message, timestamp) VALUES("%s", "%d", "%s", "%s");'
                            self.db_cursor.execute(sql % (rule["tenant_id"], SEVERITY_WARNING, message, timestamp))
                    
                    remote = IPNetwork(rule["remote_ip_prefix"])
                    if remote.is_private():
                        continue
                    
                    whitelisted = False
                    for subnet in trusted_subnets:
                        if IPNetwork(subnet).__contains__(remote):
                            whitelisted = True
                    if whitelisted:
                        continue

                    
                    if rule["remote_ip_prefix"] in ("0.0.0.0/0", "::/0"):
                        self.log.debug("Found fully opened rule in security group %s" % sg['name'])

                        all_ports = False
                        ports = "Ports " + str(rule['port_range_min']) + ':' + str(rule['port_range_max'])
                        if rule['port_range_min'] == rule['port_range_max']:
                            if rule['port_range_min'] == None:
                                all_ports = True
                            else:
                                if rule["protocol"] == "tcp":
                                    if rule['port_range_min'] in tcp_whitelist:
                                        continue
                                elif rule["protocol"] == "udp":
                                    if rule['port_range_min'] in udp_whitelist:
                                        continue
                                else:
                                    continue
                                
                                ports = "Port " + str(rule['port_range_min'])

                        # Look for matching unread alert
                        matching_alert = None
                        if all_ports:
                            pattern = "^All ports \(%s\) open all over the Internet in security group .* \(%s\) since [0-9]+ day[s]?\!$" % (rule["protocol"], sg['id'])
                        else:
                            pattern = "^%s \(%s\) open all over the Internet in security group .* \(%s\) since [0-9]+ day[s]?\!$" % (ports, rule["protocol"], sg['id'])
                        regex = re.compile(pattern)
                        
                        for alert in unread_alerts:
                            (id, user_id, message) = alert
                            if regex.match(message):
                                matching_alert = alert
                                break
                            
                        # Define alert message
                        message = ports
                        if all_ports:
                            message = "All ports"
                        message += " (" + rule["protocol"] + ") open all over the Internet in security group "
                        message += sg['name'] + " (" + sg['id'] + ") since " + str(created_delta) + " day" + created_delta_s + '!'
                        
                        # Update or keep unchanged existing alerts
                        if matching_alert:
                            if matching_alert[2] != message:
                                self.log.info("The security group %s has matching unread alert in database. Updating old messages..." % sg['id'])
                                sql = 'UPDATE user_alerts SET message="%s", timestamp="%s" WHERE id="%d";'
                                self.db_cursor.execute(sql % (message, timestamp, matching_alert[0]))
                                continue

                            self.log.debug("The security group %s has matching unread alert in database. Up to date" % sg['id'])
                            continue

                        # Create new alert
                        self.log.info("Create alert for security group %s (fully opened rule)" % sg['id'])
                        sql = 'INSERT INTO user_alerts(project, severity, message, timestamp) VALUES("%s", "%d", "%s", "%s");'
                        self.db_cursor.execute(sql % (rule["tenant_id"], SEVERITY_CRITICAL, message, timestamp))


                    elif rule['port_range_min'] == rule['port_range_max']:
                        if rule["protocol"] == "tcp":
                            if rule['port_range_min'] in tcp_whitelist:
                                continue
                        elif rule["protocol"] == "udp":
                            if rule['port_range_min'] in udp_whitelist:
                                continue
                        else:
                            continue
                            
                        self.log.debug("Found wide opened rule in security group %s" % sg['name'])

                        all_ports = False
                        ports = "Ports " + str(rule['port_range_min']) + ':' + str(rule['port_range_max'])
                        if rule['port_range_min'] == rule['port_range_max']:
                            if rule['port_range_min'] == None:
                                all_ports = True
                            else:
                                ports = "Port " + str(rule['port_range_min'])

                        # Look for matching unread alert
                        matching_alert = None
                        if all_ports:
                            pattern = "^All ports \(%s\) open to %s in security group .* \(%s\) since [0-9]+ day[s]?\.$" % (rule["protocol"], rule["remote_ip_prefix"], sg['id'])
                        else:
                            pattern = "^%s \(%s\) open to %s in security group .* \(%s\) since [0-9]+ day[s]?\.$" % (ports, rule["protocol"], rule["remote_ip_prefix"], sg['id'])
                        regex = re.compile(pattern)
                        
                        for alert in unread_alerts:
                            (id, user_id, message) = alert
                            if regex.match(message):
                                matching_alert = alert
                                break
                            
                        # Define alert message
                        message = ports
                        if all_ports:
                            message = "All ports"
                        message += " (" + rule["protocol"] + ") open to " + rule["remote_ip_prefix"] + " in security group "
                        message += sg['name'] + " (" + sg['id'] + ") since " + str(created_delta) + " day" + created_delta_s + '.'
                        
                        # Update or keep unchanged existing alerts
                        if matching_alert:
                            if matching_alert[2] != message:
                                self.log.info("The security group %s has matching unread alert in database. Updating old messages..." % sg['id'])
                                sql = 'UPDATE user_alerts SET message="%s", timestamp="%s" WHERE id="%d";'
                                self.db_cursor.execute(sql % (message, timestamp, matching_alert[0]))
                                continue

                            self.log.debug("The security group %s has matching unread alert in database. Up to date" % sg['id'])
                            continue

                        # Create new alert
                        self.log.info("Create alert for security group %s (wide opened rule)" % sg['id'])
                        sql = 'INSERT INTO user_alerts(project, severity, message, timestamp) VALUES("%s", "%d", "%s", "%s");'
                        self.db_cursor.execute(sql % (rule["tenant_id"], SEVERITY_ALERT, message, timestamp))

                            
                    else:
                        counter = 0
                        if rule["protocol"] == "tcp":
                            for port in range(rule['port_range_min'], rule['port_range_max'] + 1):
                                if not(port in tcp_whitelist):
                                    counter += 1
                        elif rule["protocol"] == "udp":
                            for port in range(rule['port_range_min'], rule['port_range_max'] + 1):
                                if not(port in udp_whitelist):
                                    counter += 1
                        else:
                            continue

                        self.log.debug("Found unknown opened rule in security group %s" % sg['name'])

                        # Look for matching unread alert
                        regex = re.compile("^[0-9]+ port[s]? in range %s:%s \(%s\) open to %s in security group .* \(%s\) since [0-9]+ day[s]?\.$" % (
                            str(rule['port_range_min']), str(rule['port_range_max']), rule["protocol"], rule["remote_ip_prefix"], sg['id'])
                        )
                        for alert in unread_alerts:
                            (id, user_id, message) = alert
                            if regex.match(message):
                                matching_alert = alert
                                break

                        # Define alert message
                        ports_en = str(counter) + " port"
                        if counter > 1:
                            ports_en += 's'
                        ports_en += " in range " + str(rule['port_range_min']) + ':' + str(rule['port_range_max'])
                        message =  ports_en + " (" + rule["protocol"] + ") open to " + rule["remote_ip_prefix"] + " in security group "
                        message += sg['name'] + " (" + sg['id'] + ") since " + str(created_delta) + " day" + created_delta_s + '.'
                        
                        # Update or keep unchanged existing alerts
                        if matching_alert:
                            if matching_alert[2] != message:
                                self.log.info("The security group %s has matching unread alert in database. Updating old messages..." % sg['id'])
                                sql = 'UPDATE user_alerts SET message="%s", timestamp="%s" WHERE id="%d";'
                                self.db_cursor.execute(sql % (message, timestamp, matching_alert[0]))
                                continue

                            self.log.debug("The security group %s has matching unread alert in database. Up to date" % sg['id'])
                            continue

                        # Create new alert
                        self.log.info("Create alert for security group %s (unknown opened rule)" % sg['id'])
                        sql = 'INSERT INTO user_alerts(project, severity, message, timestamp) VALUES("%s", "%d", "%s", "%s");'
                        self.db_cursor.execute(sql % (rule["tenant_id"], SEVERITY_ALERT, message, timestamp))

            self.log.debug("Commiting requests to database...")
            self.database.commit()
            self.log.debug("Database requests successfully commited")

        except Exception, e:
            raise gerenuk.MonitoringError(e)
