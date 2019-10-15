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
# Tue 15 Oct 10:45:56 CEST 2019


class ConfigError(Exception):
    """
    This exception is raised when a configuration error occurs.
    """

    def __init__(self, message):
        """
        Initialize the exception.
        """
        super(ConfigError, self).__init__(message)


class DependencyError(EnvironmentError):
    """
    This exception is raised when a dependency error occurs.
    """

    def __init__(self, message):
        """
        Initialize the exception.
        """
        super(DependencyError, self).__init__(message)


class MonitoringError(SystemError):
    """
    This exception is raised when a monitoring error occurs.
    """

    def __init__(self, message):
        """
        Initialize the exception.
        """
        super(MonitoringError, self).__init__(message)

class ConnectivityError(EnvironmentError):
    """
    This exception is raised when a connectivity error occurs.
    """

    def __init__(self, message):
        """
        Initialize the exception.
        """
        super(ConnectivityError, self).__init__(message)
