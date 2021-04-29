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
# Thu Apr 29 01:35:00 PM CEST 2021

import ConfigParser
import datetime
import gerenuk



class InstancesMonitorAPI():
    """
    This class is used to provide an API access to instances monitoring.
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



    def get_instances_monitoring(self, uuids):
        """
        Get monitoring data for many instances.

        :param uuids: (list) the list of instances uuid we want to get monitoring data
        :return: (dict) the requested instances monitoring data if available.
                 This dict associates uuid as keys and a monitoring dict as values.
                 Each monitoring dict associates metric as key and usage percentil as values (or -1 if data not available).
                 
        """
        sql = "SELECT * FROM instances_monitoring"
        operator = " WHERE"
        for uuid in uuids:
            sql += "%s uuid='%s'" % (operator, uuid)
            operator = " OR"

        monitoring = dict()

        if len(uuids) > 0:
            self.db_cursor.execute(sql)
            rows = self.db_cursor.fetchall()

            for row in rows:
                (uuid, hypervisor, vcores, vram) = row[0:4]
                (hourly_vcpu_usage, daily_vcpu_usage, weekly_vcpu_usage) = row[4:7]
                (hourly_cpu_usage, daily_cpu_usage, weekly_cpu_usage) = row[7:10]
                (hourly_mem_usage, daily_mem_usage, weekly_mem_usage) = row[10:13]
                (deleted, last_update) = row[13:]

                if uuid in monitoring:
                    continue

                if deleted == 1:
                    continue
                
                info = {"hypervisor": hypervisor, "vcores": vcores, "vmem": vram, "updated": last_update}
                monitoring[uuid] = {"info": info, "vcpu": tuple(), "cpu": tuple(), "mem": tuple()}

                if len(hourly_vcpu_usage) > 0:
                    hourly_vcpu_average = sum(float(n) for n in hourly_vcpu_usage.split(',') if len(n) > 0) / float(len(hourly_vcpu_usage.split(',')))
                else:
                    hourly_vcpu_average = -1.

                if len(hourly_cpu_usage) > 0:
                    hourly_cpu_average = sum(float(n) for n in hourly_cpu_usage.split(',') if len(n) > 0) / float(len(hourly_cpu_usage.split(',')))
                else:
                    hourly_cpu_average = -1.

                if len(hourly_mem_usage) > 0:
                    hourly_mem_average = sum(float(n) for n in hourly_mem_usage.split(',') if len(n) > 0) / float(len(hourly_mem_usage.split(',')))
                else:
                    hourly_mem_average = -1.

                if len(daily_vcpu_usage) > 0:
                    daily_vcpu_average = sum(float(n) for n in daily_vcpu_usage.split(',') if len(n) > 0) / float(len(daily_vcpu_usage.split(',')))
                else:
                    daily_vcpu_average = -1.

                if len(daily_cpu_usage) > 0:
                    daily_cpu_average = sum(float(n) for n in daily_cpu_usage.split(',') if len(n) > 0) / float(len(daily_cpu_usage.split(',')))
                else:
                    daily_cpu_average = -1.

                if len(daily_mem_usage) > 0:
                    daily_mem_average = sum(float(n) for n in daily_mem_usage.split(',') if len(n) > 0) / float(len(daily_mem_usage.split(',')))
                else:
                    daily_mem_average = -1.

                if len(weekly_vcpu_usage) > 0:
                    weekly_vcpu_average = sum(float(n) for n in weekly_vcpu_usage.split(',') if len(n) > 0) / float(len(weekly_vcpu_usage.split(',')))
                else:
                    weekly_vcpu_average = -1.

                if len(weekly_cpu_usage) > 0:
                    weekly_cpu_average = sum(float(n) for n in weekly_cpu_usage.split(',') if len(n) > 0) / float(len(weekly_cpu_usage.split(',')))
                else:
                    weekly_cpu_average = -1.

                if len(weekly_mem_usage) > 0:
                    weekly_mem_average = sum(float(n) for n in weekly_mem_usage.split(',') if len(n) > 0) / float(len(weekly_mem_usage.split(',')))
                else:
                    weekly_mem_average = -1.

                monitoring[uuid]["vcpu"] = {'hourly': round(hourly_vcpu_average, 2), 'daily': round(daily_vcpu_average, 2), 'weekly': round(weekly_vcpu_average, 2)}
                monitoring[uuid]["cpu"] = {'hourly': round(hourly_cpu_average, 2), 'daily': round(daily_cpu_average, 2), 'weekly': round(weekly_cpu_average, 2)}
                monitoring[uuid]["mem"] = {'hourly': round(hourly_mem_average, 2), 'daily': round(daily_mem_average, 2), 'weekly': round(weekly_mem_average, 2)}

        return monitoring
