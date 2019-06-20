#!/usr/bin/python2
# -*- coding: utf-8 -*-
#
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
# Thu 20 Jun 11:23:53 CEST 2019

NOVA_API_VERSION = 2
CINDER_API_VERSION = 3

SEVERITY_INFO = 0
SEVERITY_ALERT = 1
SEVERITY_WARNING = 2
SEVERITY_CRITICAL = 3


from netaddr import *
import datetime
import gerenuk
import os



class OpenstackMonitor():
    """
    This class is used to monitor OpenStack.
    """

    def __init__(self, config):
        """
        Initialize OpenstackMonitor object.

        :param config: (gerenuk.Config) The gerenuk configuration
        """
        # Dependencies
        try:
            import mysql.connector
        except Exception, e:
            raise gerenuk.DependencyError(e)

        # Config
        self.config = config

        # MySQL
        self.database = mysql.connector.connect(
            host=self.config.get("database", "db_host"),
            user=self.config.get("database", "db_user"),
            password=self.config.get("database", "db_pass"),
            database=self.config.get("database", "db_name")
        )
        self.db_cursor = self.database.cursor()



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


    
    def projects_lookup(self):
        """
        Browse all monitored projects from config files.
        """
        projects_dir = self.config.get("openstack", "projects_dir")
        projects = os.listdir(projects_dir)

        for project in projects:
            if not(project[-5:] == ".conf"):
                continue

            project_config = gerenuk.Config()
            project_config.load(projects_dir + "/" + project)

            self.monitor_project(project_config)


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

        auth = keystone_identity.v3.Password(**credentials)
        session = keystone_session.Session(auth=auth)
        keystone = keystone_client.Client(session=session)
        nova = nova_client.Client(NOVA_API_VERSION, session=session)
        cinder = cinder_client.Client(CINDER_API_VERSION, session=session)
        neutron = neutron_client.Client(session=session)

        now = datetime.date.today()
        timestamp = datetime.datetime.now()

        try:
            # Instances
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
                    message_en = "Instance " + instance.id
                    if instance.name:
                        message_en += " (" + instance.name + ")"
                    message_en += " created on " + created_at.strftime("%d/%m/%Y") + " (" + str(created_delta) + " day" + created_delta_s + " ago) in error ("
                    message_en += instance.status.upper() + ") since " + str(updated_delta) + " day" + updated_delta_s + '.'

                    message_fr = "Instance " + instance.id
                    if instance.name:
                        message_fr += " (" + instance.name + ")"
                    message_fr += u" créée le " + created_at.strftime("%d/%m/%Y") + " (il y a " + str(created_delta) + " jour" + created_delta_s + ") en erreur ("
                    message_fr += instance.status.upper() + ") depuis " + str(updated_delta) + " jour" + updated_delta_s + '.'
                    
                    sql = 'SELECT COUNT(id) AS nb FROM user_alerts WHERE status=1 AND message_en="%s";'
                    self.db_cursor.execute(sql % (message_en,))
                    if self.db_cursor.fetchone()[0] == 0:
                        sql = 'INSERT INTO user_alerts(uuid, project, severity, message_fr, message_en, timestamp) VALUES("%s", "%s", "%d", "%s", "%s", "%s");'
                        self.db_cursor.execute(sql % (instance.user_id, instance.tenant_id, SEVERITY_WARNING, message_fr, message_en, timestamp))
                
                elif instance.status.upper() == "SHUTOFF":
                    if updated_delta >= project_config.get_int('instances', 'stopped_alert_delay'):
                        message_en = "Instance " + instance.id
                        if instance.name:
                            message_en += " (" + instance.name + ")"
                        message_en += " created on " + created_at.strftime("%d/%m/%Y") + " (" + str(created_delta) + " day" + created_delta_s + " ago) stopped ("
                        message_en += instance.status.upper() + ") since " + str(updated_delta) + " day" + updated_delta_s + '.'

                        message_fr = "Instance " + instance.id
                        if instance.name:
                            message_fr += " (" + instance.name + ")"
                        message_fr += u" creéée le " + created_at.strftime("%d/%m/%Y") + " (il y a " + str(created_delta) + " jour" + created_delta_s + u") éteinte ("
                        message_fr += instance.status.upper() + ") depuis " + str(updated_delta) + " jour" + updated_delta_s + '.'
                        
                        sql = 'SELECT COUNT(id) AS nb FROM user_alerts WHERE status=1 AND message_en="%s";'
                        self.db_cursor.execute(sql % (message_en,))
                        if self.db_cursor.fetchone()[0] == 0:
                            sql = 'INSERT INTO user_alerts(uuid, project, severity, message_fr, message_en, timestamp) VALUES("%s", "%s", "%d", "%s", "%s", "%s");'
                            self.db_cursor.execute(sql % (instance.user_id, instance.tenant_id, SEVERITY_ALERT, message_fr, message_en, timestamp))
                
                elif instance.status.upper() == "ACTIVE":
                    if updated_delta >= project_config.get_int('instances', 'running_alert_delay'):
                        message_en = "Instance " + instance.id
                        if instance.name:
                            message_en += " (" + instance.name + ")"
                        message_en += " created on " + created_at.strftime("%d/%m/%Y") + " (" + str(created_delta) + " day" + created_delta_s + " ago) running ("
                        message_en += instance.status.upper() + ") since a long time (" + str(updated_delta) + " day" + updated_delta_s + ")."

                        message_fr = "Instance " + instance.id
                        if instance.name:
                            message_fr += " (" + instance.name + ")"
                        message_fr += u" creéée le " + created_at.strftime("%d/%m/%Y") + " (il y a " + str(created_delta) + " jour" + created_delta_s + u") allumée ("
                        message_fr += instance.status.upper() + ") depuis longtemps (" + str(updated_delta) + " jour" + updated_delta_s + ")."
                        
                        sql = 'SELECT COUNT(id) AS nb FROM user_alerts WHERE status=1 AND message_en="%s";'
                        self.db_cursor.execute(sql % (message_en,))
                        if self.db_cursor.fetchone()[0] == 0:
                            sql = 'INSERT INTO user_alerts(uuid, project, severity, message_fr, message_en, timestamp) VALUES("%s", "%s", "%d", "%s", "%s", "%s");'
                            self.db_cursor.execute(sql % (instance.user_id, instance.tenant_id, SEVERITY_INFO, message_fr, message_en, timestamp))

            # Volumes
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
                    message_en = "Volume " + volume.id
                    if volume.name:
                        message_en += " (" + volume.name + ")"
                    message_en += " created on " + created_at.strftime("%d/%m/%Y") + " (" + str(created_delta) + " day" + created_delta_s + "  ago) in error ("
                    message_en += volume.status.upper() + ") since " + str(updated_delta) + " day" + updated_delta_s + '.'

                    message_fr = "Volume " + volume.id
                    if volume.name:
                        message_fr += " (" + volume.name + ")"
                    message_fr += u" créée le " + created_at.strftime("%d/%m/%Y") + " (il y a " + str(created_delta) + " jour" + created_delta_s + " ) en erreur ("
                    message_fr += volume.status.upper() + ") depuis " + str(updated_delta) + " jour" + updated_delta_s + '.'
                    
                    sql = 'SELECT COUNT(id) AS nb FROM user_alerts WHERE status=1 AND message_en="%s";'
                    self.db_cursor.execute(sql % (message_en,))
                    if self.db_cursor.fetchone()[0] == 0:
                        sql = 'INSERT INTO user_alerts(uuid, project, severity, message_fr, message_en, timestamp) VALUES("%s", "%s", "%d", "%s", "%s", "%s");'
                        self.db_cursor.execute(sql % (volume.user_id, getattr(volume, "os-vol-tenant-attr:tenant_id"), SEVERITY_WARNING, message_fr, message_en, timestamp))

                elif volume.status.upper() == "AVAILABLE":
                    if not(volume.bootable) and not(volume.name):
                        if updated_delta >= project_config.get_int('volumes', 'orphan_alert_delay'):
                            message_en = "Volume " + volume.id
                            message_en += " created on " + created_at.strftime("%d/%m/%Y") + " (" + str(created_delta) + " day" + created_delta_s + "  ago) probably orphan ("
                            message_en += volume.status.upper() + ") since " + str(updated_delta) + " day" + updated_delta_s + '.'

                            message_fr = "Volume " + volume.id
                            message_fr += u" créée le " + created_at.strftime("%d/%m/%Y") + " (il y a " + str(created_delta) + " jour" + created_delta_s + " ) probablement orphelin ("
                            message_fr += volume.status.upper() + ") depuis " + str(updated_delta) + " jour" + updated_delta_s + '.'
                        
                            sql = 'SELECT COUNT(id) AS nb FROM user_alerts WHERE status=1 AND message_en="%s";'
                            self.db_cursor.execute(sql % (message_en,))
                            if self.db_cursor.fetchone()[0] == 0:
                                sql = 'INSERT INTO user_alerts(uuid, project, severity, message_fr, message_en, timestamp) VALUES("%s", "%s", "%d", "%s", "%s", "%s");'
                                self.db_cursor.execute(sql % (volume.user_id, getattr(volume, "os-vol-tenant-attr:tenant_id"), SEVERITY_ALERT, message_fr, message_en, timestamp))
                            
                    else:
                        if updated_delta >= project_config.get_int('volumes', 'inactive_alert_delay'):
                            message_en = "Volume " + volume.id
                            if volume.name:
                                message_en += " (" + volume.name + ")"
                            message_en += " created on " + created_at.strftime("%d/%m/%Y") + " (" + str(created_delta) + " day" + created_delta_s + "  ago) inactive ("
                            message_en += volume.status.upper() + ") since " + str(updated_delta) + " day" + updated_delta_s + '.'

                            message_fr = "Volume " + volume.id
                            if volume.name:
                                message_fr += " (" + volume.name + ")"
                            message_fr += u" créée le " + created_at.strftime("%d/%m/%Y") + " (il y a " + str(created_delta) + " jour" + created_delta_s + u" ) non utilisé ("
                            message_fr += volume.status.upper() + ") depuis " + str(updated_delta) + " jour" + updated_delta_s + '.'

                            sql = 'SELECT COUNT(id) AS nb FROM user_alerts WHERE status=1 AND message_en="%s";'
                            self.db_cursor.execute(sql % (message_en,))
                            if self.db_cursor.fetchone()[0] == 0:
                                sql = 'INSERT INTO user_alerts(uuid, project, severity, message_fr, message_en, timestamp) VALUES("%s", "%s", "%d", "%s", "%s", "%s");'
                                self.db_cursor.execute(sql % (volume.user_id, getattr(volume, "os-vol-tenant-attr:tenant_id"), SEVERITY_ALERT, message_fr, message_en, timestamp))

            # Security Groups
            for sg in neutron.list_security_groups()['security_groups']:
                trusted_subnets = project_config.get_list('networks', 'trusted_subnets')
                tcp_whitelist = project_config.get_list('networks', 'tcp_whitelist')
                udp_whitelist = project_config.get_list('networks', 'udp_whitelist')
                
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
                            message_en = "User defined rules in default security group (reminder: it's forbidden)!"
                            message_fr = u"Règles définies par des utilisateurs présentes dans le groupe de sécurité default (rappel: c'est interdit) !"

                            sql = 'SELECT COUNT(id) AS nb FROM user_alerts WHERE status=1 AND message_en="%s";'
                            self.db_cursor.execute(sql % (message_en,))
                            if self.db_cursor.fetchone()[0] == 0:
                                sql = 'INSERT INTO user_alerts(project, severity, message_fr, message_en, timestamp) VALUES("%s", "%d", "%s", "%s", "%s");'
                                self.db_cursor.execute(sql % (rule["tenant_id"], SEVERITY_WARNING, message_fr, message_en, timestamp))
                    
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
                        all_ports = False
                        ports = "Ports " + str(rule['port_range_min']) + ':' + str(rule['port_range_max'])
                        if rule['port_range_min'] == rule['port_range_max']:
                            if rule['port_range_min'] == None:
                                all_ports = True
                            else:
                                ports = "Port " + str(rule['port_range_min'])

                        message_en = ports
                        if all_ports:
                            message_en = "All ports"
                        message_en += " (" + rule["protocol"] + ") open all over the Internet in security group "
                        message_en += sg['name'] + " (" + sg['id'] + ") since " + str(created_delta) + " day" + created_delta_s + '!'
                        
                        message_fr = ports
                        if all_ports:
                            message_fr = u"Intégralité des ports"
                        message_fr += " (" + rule["protocol"] + u") ouverts à l'ensemble d'Internet dans le groupe de sécurité "
                        message_fr += sg['name'] + " (" + sg['id'] + ") depuis " + str(created_delta) + " jour" + created_delta_s + '!'

                        sql = 'SELECT COUNT(id) AS nb FROM user_alerts WHERE status=1 AND message_en="%s";'
                        self.db_cursor.execute(sql % (message_en,))
                        if self.db_cursor.fetchone()[0] == 0:
                            sql = 'INSERT INTO user_alerts(project, severity, message_fr, message_en, timestamp) VALUES("%s", "%d", "%s", "%s", "%s");'
                            self.db_cursor.execute(sql % (rule["tenant_id"], SEVERITY_CRITICAL, message_fr, message_en, timestamp))

                    elif rule['port_range_min'] == rule['port_range_max']:
                        if rule["protocol"] == "tcp":
                            if rule['port_range_min'] in tcp_whitelist:
                                continue
                        elif rule["protocol"] == "udp":
                            if rule['port_range_min'] in tcp_whitelist:
                                continue
                        else:
                            continue
                            
                        all_ports = False
                        ports = "Ports " + str(rule['port_range_min']) + ':' + str(rule['port_range_max'])
                        if rule['port_range_min'] == rule['port_range_max']:
                            if rule['port_range_min'] == None:
                                all_ports = True
                            else:
                                ports = "Port " + str(rule['port_range_min'])

                        message_en = ports
                        if all_ports:
                            message_en = "All ports"
                        message_en += " (" + rule["protocol"] + ") open to " + rule["remote_ip_prefix"] + " in security group "
                        message_en += sg['name'] + " (" + sg['id'] + ") since " + str(created_delta) + " day" + created_delta_s + '.'
                        
                        message_fr = ports
                        if all_ports:
                            message_fr = u"Intégralité des ports"
                        message_fr += " (" + rule["protocol"] + u") ouverts à " + rule["remote_ip_prefix"] + u" dans le groupe de sécurité "
                        message_fr += sg['name'] + " (" + sg['id'] + ") depuis " + str(created_delta) + " jour" + created_delta_s + '.'

                        sql = 'SELECT COUNT(id) AS nb FROM user_alerts WHERE status=1 AND message_en="%s";'
                        self.db_cursor.execute(sql % (message_en,))
                        if self.db_cursor.fetchone()[0] == 0:
                            sql = 'INSERT INTO user_alerts(project, severity, message_fr, message_en, timestamp) VALUES("%s", "%d", "%s", "%s", "%s");'
                            self.db_cursor.execute(sql % (rule["tenant_id"], SEVERITY_ALERT, message_fr, message_en, timestamp))
                    
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

                        ports_en = str(counter) + " port"
                        if counter > 1:
                            ports_en += 's'
                        ports_en += " in range " + str(rule['port_range_min']) + ':' + str(rule['port_range_max'])
                        message_en =  ports_en + " (" + rule["protocol"] + ") open to " + rule["remote_ip_prefix"] + " in security group "
                        message_en += sg['name'] + " (" + sg['id'] + ") since " + str(created_delta) + " day" + created_delta_s + '.'
                        
                        ports_fr = str(counter) + " port"
                        if counter > 1:
                            ports_fr += 's'
                        ports_fr += " dans l'intervalle " + str(rule['port_range_min']) + ':' + str(rule['port_range_max'])
                        message_fr = ports_fr + " (" + rule["protocol"] + u") ouverts à " + rule["remote_ip_prefix"] + u" dans le groupe de sécurité "
                        message_fr += sg['name'] + " (" + sg['id'] + ") depuis " + str(created_delta) + " jour" + created_delta_s + '.'

                        sql = 'SELECT COUNT(id) AS nb FROM user_alerts WHERE status=1 AND message_en="%s";'
                        self.db_cursor.execute(sql % (message_en,))
                        if self.db_cursor.fetchone()[0] == 0:
                            sql = 'INSERT INTO user_alerts(project, severity, message_fr, message_en, timestamp) VALUES("%s", "%d", "%s", "%s", "%s");'
                            self.db_cursor.execute(sql % (rule["tenant_id"], SEVERITY_ALERT, message_fr, message_en, timestamp))
            self.database.commit()

        except Exception, e:
            raise gerenuk.MonitoringError(e)
