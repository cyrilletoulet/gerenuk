#!/usr/bin/python2
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
# Wed 24 Apr 07:45:24 CEST 2019

import multiprocessing
import ConfigParser
import platform
import datetime
import gerenuk
import psutil
import time
import sys
import os



class LibvirtMonitor():
    """
    This class is used to monitor LibVirt.
    """

    def __init__(self, config):
        """
        Initialize the LibvirtMonitor object

        :raise: (gerenuk.DependencyError) When a required dependency is missing
        :raise: (gerenuk.MonitoringError) When an internal error occurs
        """
        # Dependencies
        try:
            import libvirt
            import mysql.connector
        except Exception, e:
            raise gerenuk.DependencyError(e)

        # Config
        self.config = config

        # Constants
        self.NB_VALUES = {
            "hourly": 3600 / self.config.getint("libvirtmon", "monitoring_frequency"),
            "daily": 24,
            "weekly": 7
        }

        # LibVirt
        self.connection = libvirt.openReadOnly(None)
        if self.connection == None:
            raise gerenuk.MonitoringError('Failed to open connection to libvirtd')

        # MySQL
        self.database = mysql.connector.connect(
            host=self.config.get("DEFAULT", "db_host"),
            user=self.config.get("DEFAULT", "db_user"),
            password=self.config.get("DEFAULT", "db_pass"),
            database=self.config.get("DEFAULT", "db_name")
        )
        self.db_cursor = self.database.cursor()

        # Hypervisor information
        self.hypervisor = dict()
        self.hypervisor["hostname"] = platform.node()
        self.hypervisor["cores"] = multiprocessing.cpu_count()
        self.hypervisor["memory"] = dict(psutil.virtual_memory()._asdict())["total"]
        self.hypervisor["estimated_memory"] = self.hypervisor["memory"] / 1024**2
        coe = self.hypervisor["estimated_memory"] // 4096
        if 4096 * coe < self.hypervisor["estimated_memory"] < 4096 * (coe+1):
            self.hypervisor["estimated_memory"] = 4096 * (coe+1)

        # Stats
        self.monitoring = dict()
        self.loaded_stats = list()
        self.load_stats()



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
        desc  = u"Hypervisor: \n"
        desc += u" - Hostname: " + self.hypervisor["hostname"] + "\n"
        desc += u" - RAM: " + str(self.hypervisor["estimated_memory"]) + " MB (" + str(self.hypervisor["estimated_memory"] / 1024) + " GB)" + "\n"

        return desc


    
    def collect_stats(self):
        """
        Colelct all libvirt domains stats.
        """
        domain_ids = self.connection.listDomainsID()
        for domain_id in domain_ids:
            domain = self.connection.lookupByID(domain_id)

            vcpu = domain.maxVcpus()
            vram = domain.maxMemory() / 1024

            cpu_stats_1 = domain.getCPUStats(True)
            mem_stats_1 = domain.memoryStats()
            time.sleep(self.config.getint("libvirtmon", "sampling_time"))
            cpu_stats_2 = domain.getCPUStats(True)
            mem_stats_2 = domain.memoryStats()

            t1 = cpu_stats_1[0]["cpu_time"]
            t2 = cpu_stats_2[0]["cpu_time"]

            cpu_usage = (t2 - t1) / vcpu / 10.**9 / self.config.getint("libvirtmon", "sampling_time")
            real_cpu_usage = (t2 - t1) / self.hypervisor["cores"] / 10.**9 / self.config.getint("libvirtmon", "sampling_time")
            mem_stats_average = (mem_stats_1["actual"] + mem_stats_2["actual"]) / 2.
            mem_usage = (mem_stats_average / 1024 / self.hypervisor["estimated_memory"])

            stats = dict()
            stats["uuid"] = domain.UUIDString()
            stats["vcpu"] = vcpu
            stats["vram"] = vram
            stats["vcpu_usage"] = round(cpu_usage * 100., 2)
            stats["cpu_usage"] = round(real_cpu_usage * 100., 2)
            stats["mem_usage"] = round(mem_usage * 100., 2)

            self.store_stats(stats)

        self.save_stats()



    def load_stats(self):
        """
        Load all collected stats from database.
        """
        local_uuids = list()
        sql = "SELECT * FROM instances_monitoring"

        operator = " WHERE"
        domain_ids = self.connection.listDomainsID()
        for domain_id in domain_ids:
            domain = self.connection.lookupByID(domain_id)
            local_uuids.append(domain.UUIDString())
            sql += "%s uuid='%s'" % (operator, domain.UUIDString())
            operator = " OR"

        if len(local_uuids) > 0:
            self.db_cursor.execute(sql)
            rows = self.db_cursor.fetchall()

            for row in rows:
                (uuid, hypervisor, vcores, vram) = row[0:4]
                (hourly_vcpu_usage, daily_vcpu_usage, weekly_vcpu_usage) = row[4:7]
                (hourly_cpu_usage, daily_cpu_usage, weekly_cpu_usage) = row[7:10]
                (hourly_mem_usage, daily_mem_usage, weekly_mem_usage) = row[10:13]
                (deleted, last_update) = row[13:]

                if not uuid in self.monitoring:
                    self.monitoring[uuid] = {
                        "hourly": {"vcpu": [], "cpu": [], "mem": []},
                        "daily": {"vcpu": [], "cpu": [], "mem": []},
                        "weekly": {"vcpu": [], "cpu": [], "mem": []}
                    }

                self.monitoring[uuid]["hourly"]["vcpu"] += [float(n) for n in hourly_vcpu_usage.split(',')]
                self.monitoring[uuid]["hourly"]["cpu"] += [float(n) for n in hourly_cpu_usage.split(',')]
                self.monitoring[uuid]["hourly"]["mem"] += [float(n) for n in hourly_mem_usage.split(',')]

                self.loaded_stats.append(uuid)



    def store_stats(self, stats):
        """
        Store and rotate instance stats.

        :param stats: (tuple) the instance stats to store
        """
        uuid = stats["uuid"]
        now = datetime.datetime.now()

        if not uuid in self.monitoring:
            self.monitoring[uuid] = {
                "hourly": {"vcpu": [], "cpu": [], "mem": []},
                "daily": {"vcpu": [], "cpu": [], "mem": []},
                "weekly": {"vcpu": [], "cpu": [], "mem": []}
            }

        # Hourly
        self.monitoring[uuid]["hourly"]["vcpu"].append(stats["vcpu_usage"])
        self.monitoring[uuid]["hourly"]["cpu"].append(stats["cpu_usage"])
        self.monitoring[uuid]["hourly"]["mem"].append(stats["mem_usage"])

        # Daily
        if now.minute <= (self.config.getint("libvirtmon", "monitoring_frequency") / 60):
            hourly_vcpu_average = sum(float(i) for i in self.monitoring[uuid]["hourly"]["vcpu"]) / float(len(self.monitoring[uuid]["hourly"]["vcpu"]))
            hourly_cpu_average = sum(float(i) for i in self.monitoring[uuid]["hourly"]["cpu"]) / float(len(self.monitoring[uuid]["hourly"]["cpu"]))
            hourly_mem_average = sum(float(i) for i in self.monitoring[uuid]["hourly"]["mem"]) / float(len(self.monitoring[uuid]["hourly"]["mem"]))

            self.monitoring[uuid]["daily"]["vcpu"].append(hourly_vcpu_average)
            self.monitoring[uuid]["daily"]["cpu"].append(hourly_cpu_average)
            self.monitoring[uuid]["daily"]["mem"].append(hourly_mem_average)

        # Weekly
        if now.minute <= (self.config.getint("libvirtmon", "monitoring_frequency") / 60) and now.hour == 0:
            daily_vcpu_average = sum(float(i) for i in self.monitoring[uuid]["daily"]["vcpu"]) / float(len(self.monitoring[uuid]["daily"]["vcpu"]))
            daily_cpu_average = sum(float(i) for i in self.monitoring[uuid]["daily"]["cpu"]) / float(len(self.monitoring[uuid]["daily"]["cpu"]))
            daily_mem_average = sum(float(i) for i in self.monitoring[uuid]["daily"]["mem"]) / float(len(self.monitoring[uuid]["daily"]["mem"]))

            self.monitoring[uuid]["weekly"]["vcpu"].append(daily_vcpu_average)
            self.monitoring[uuid]["weekly"]["cpu"].append(daily_cpu_average)
            self.monitoring[uuid]["weekly"]["mem"].append(daily_mem_average)

        # Rotate
        for period in ["hourly", "daily", "weekly"]:
            for metric in ["vcpu", "cpu", "mem"]:
                if len(self.monitoring[uuid][period][metric]) > self.NB_VALUES[period]:
                    self.monitoring[uuid][period][metric] = self.monitoring[uuid][period][metric][1:self.NB_VALUES[period]+1]



    def save_stats(self):
        """
        Save all collected stats to database.
        """
        for uuid in self.monitoring:
            if uuid in self.loaded_stats:
                # UPDATE
                now = datetime.datetime.now()

                sql = 'UPDATE instances_monitoring SET deleted="0", last_update="%s", '
                sql += 'hourly_vcpu_usage="%s", hourly_cpu_usage="%s", hourly_mem_usage="%s", '
                sql += 'daily_vcpu_usage="%s", daily_cpu_usage="%s", daily_mem_usage="%s", '
                sql += 'weekly_vcpu_usage="%s", weekly_cpu_usage="%s", weekly_mem_usage="%s" '
                sql += 'WHERE uuid="%s";'

                values = (now,)
                for period in ["hourly", "daily", "weekly"]:
                    for metric in ["vcpu", "cpu", "mem"]:
                        values += (','.join(str("%.1f" % d) for d in self.monitoring[uuid][period][metric]),)
                values += (uuid,)

                self.db_cursor.execute(sql % values)

            else:
                # INSERT
                fields = ['uuid', 'hypervisor', 'vcores', 'vram']
                fields += ['hourly_vcpu_usage', 'daily_vcpu_usage', 'weekly_vcpu_usage']
                fields += ['hourly_cpu_usage', 'daily_cpu_usage', 'weekly_cpu_usage']
                fields += ['hourly_mem_usage', 'daily_mem_usage', 'weekly_mem_usage']

                sql = 'INSERT INTO instances_monitoring (' + ', '.join(fields) + ') VALUES ("%s", "%s", "%d", "%d"' + ', "%s"'*9 + ');'

                values = (uuid, self.hypervisor["hostname"], self.hypervisor["cores"], self.hypervisor["estimated_memory"])
                values += (str("%.1f" % self.monitoring[uuid]["hourly"]["vcpu"][0]), '', '')
                values += (str("%.1f" % self.monitoring[uuid]["hourly"]["cpu"][0]), '', '')
                values += (str("%.1f" % self.monitoring[uuid]["hourly"]["mem"][0]), '', '')

                self.db_cursor.execute(sql % values)
                self.loaded_stats.append(uuid)

        self.database.commit()
