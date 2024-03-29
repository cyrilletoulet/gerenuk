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
# Mon Oct 25 12:56:40 PM CEST 2021

from setuptools import find_packages, setup


setup(
    name = "gerenuk",
    version = "2.0.1",
    description = "A cloud monitoring tools set",
    url = "https://github.com/cyrilletoulet/gerenuk",

    license = 'GPL',
    classifiers = [
        "License :: OSI Approved :: GPL v3 license",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],

    keywords = "monitoring cloud openstack libvirt",

    author = "Cyrille TOULET",
    author_email = "cyrille.toulet@univ-lille.fr",

    package_data = {'': ["README", "*.conf"]},
    packages = find_packages(),

    python_requires = '>=3.6',
)
