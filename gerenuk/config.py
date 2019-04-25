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
# Wed 17 Apr 10:57:25 CEST 2019


from . import BASE_PATH
from .exceptions import ConfigError
import ConfigParser
import sys
import os


class Config():
    """
    This Gerenuk config manager.
    """

    def __init__(self):
        """
        Initialize the Config object.
        """
        self.config = ConfigParser.ConfigParser()
        self.load(BASE_PATH + "/defaults.conf")


    def load(self, config_file):
        """
        Initialize Config object.

        :param config_file: (str) The configuration file to load
        """
        if not os.path.isfile(config_file):
            raise ConfigError("configuration file " + config_file + " not found")

        self.config.read(config_file)


    def get(self, section, option):
        """
        Get an option value for the named section.

        :param section: (str) The section to looking in
        :param option: (str) The option to looking for
        :return: (str) The configuration item if exists
        """
        return self.config.get(section, option)


    def getint(self, section, option):
        """
        Get an integer option value for the named section.

        :param section: (str) The section to looking in
        :param option: (str) The option to looking for
        :return: (int) The configuration item if exists
        """
        return self.config.getint(section, option)