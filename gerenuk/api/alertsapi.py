#!/usr/bin/python3
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
# Thu Apr 29 01:22:51 PM CEST 2021

import configparser
import datetime
import gerenuk



class AlertsAPI():
    """
    This class is used to provide an API access to alerts.
    """

    def __init__(self, config):
        """
        Initialize the LibvirtMonitor object

        :raise: (gerenuk.DependencyError) When a required dependency is missing
        :raise: (gerenuk.MonitoringError) When an internal error occurs
        """
        # Dependencies
        try:
            import mysql.connector
        except Exception as e:
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



    def get_unread_alerts(self, project_id):
        """
        Get all unread alerts for a specific project.

        :param project_id: (str) project uuid concerned by alerts
        :return: (list) list of alerts dicts
                 
        """
        sql = "SELECT id, uuid, project, severity, status, message, timestamp FROM user_alerts WHERE project='%s' AND status='1';"

        self.db_cursor.execute(sql % (project_id,))
        rows = self.db_cursor.fetchall()

        alerts = list()
        
        for row in rows:
            (id, uuid, project, severity, status, message, timestamp) = row
            alert = {
                "id": id,
                "uuid": uuid,
                "project": project,
                "severity": severity,
                "status": status,
                "message": message,
                "timestamp": timestamp
            }
            alerts.append(alert)
            
        return alerts


    def get_read_alerts(self, project_id):
        """
        Get all read alerts for a specific project.

        :param project_id: (str) project uuid concerned by alerts
        :return: (list) list of alerts dicts
                 
        """
        sql = "SELECT id, uuid, project, severity, status, message, timestamp FROM user_alerts WHERE project='%s' AND status='0';"

        self.db_cursor.execute(sql % (project_id,))
        rows = self.db_cursor.fetchall()

        alerts = list()
        
        for row in rows:
            (id, uuid, project, severity, status, message, timestamp) = row
            alert = {
                "id": id,
                "uuid": uuid,
                "project": project,
                "severity": severity,
                "status": status,
                "message": message,
                "timestamp": timestamp
            }
            alerts.append(alert)
            
        return alerts


    def tag_alerts_as_read(self, alerts):
        """
        Tag alert(s) as read.

        :param alerts: (list) the alerts IDs
        """
        for alert_id in alerts:
            sql = "UPDATE user_alerts SET status='0' WHERE id='%d';"
            self.db_cursor.execute(sql % (alert_id,))

        self.database.commit()


    def tag_alerts_as_unread(self, alerts):
        """
        Tag alert(s) as unread.

        :param alerts: (list) the alerts IDs
        """
        for alert_id in alerts:
            sql = "UPDATE user_alerts SET status='1' WHERE id='%d';"
            self.db_cursor.execute(sql % (alert_id,))

        self.database.commit()
