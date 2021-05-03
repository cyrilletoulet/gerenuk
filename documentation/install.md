# Gerenuk installation

## 1. Compatibility

| OpenStack release | Gerenuk release |
| --- | --- |
| Ussuri | 2.0.x |
| Train | 1.4.x |
| Stein | 1.4.x |
| Rocky | 1.3.x |
| Queen | 1.3.x |





## 2. Prerequisites
### 2.1. Minimal deployment

On all servers, install the required python packages: 
```bash
yum install python3-pip
pip3 install mysql-connector-python
```

To install gerenuk lib from distribution tarball:
```bash
pip3 install gerenuk-x.y.z.tar.gz
```

To remove the installed gerenuk lib:
```bash
pip3 uninstall gerenuk
```

Finally, create the config directory:
```bash
mkdir -p /etc/gerenuk/project.d
chmod -R 711 /etc/gerenuk
touch /etc/gerenuk/gerenuk.conf
chmod 600 /etc/gerenuk/gerenuk.conf
```

### 2.2. Database initialization
Gerenuk also needs to store collected data in a MySQL-like database.

Create the required database on a service node, like cloud controller:
```bash
mysql -u root -h $DB_HOST -p -e "CREATE DATABASE gerenuk;"
mysql -u root -h $DB_HOST -p -e "CREATE USER 'gerenuk'@'%' IDENTIFIED BY '*secret*';"
mysql -u root -h $DB_HOST -p -e "CREATE USER 'gerenuk_dashboard'@'%' IDENTIFIED BY '*secret*';"
mysql -u root -h $DB_HOST -p -e "GRANT ALL PRIVILEGES ON gerenuk.* TO 'gerenuk'@'%';"
mysql -u root -h $DB_HOST -p -e "GRANT SELECT, UPDATE ON gerenuk.* TO 'gerenuk_dashboard'@'%';"
```
Please replace *secret* by suitable passwords.

Next, configure database in **/etc/gerenuk/gerenuk.conf** (see config reference for details):
```
[database]
db_host = DB_HOST
db_name = gerenuk
db_user = gerenuk
db_pass = *secret*
```

You can now populate the database:
```bash
./bin/gerenuk-db-wizard -c /etc/gerenuk/gerenuk.conf
```





## 3. Install Gerenuk on cloud controller
First of all, follow the previous common prerequisites.

### 3.1. Database configuration
Next, configure database in **/etc/gerenuk/gerenuk.conf** (see config reference for details):
```
[database]
db_host = DB_HOST
db_name = gerenuk
db_user = gerenuk
db_pass = *secret*
```


### 3.2. Gerenuk service
Start by installing daemons:
```bash
cp bin/gerenuk-openstackmon /usr/bin/
cp systemd/gerenuk-openstackmon.service /usr/lib/systemd/system/
systemctl daemon-reload
```

And finally, start the **gerenuk-openstackmon** service:
```bash
systemctl start gerenuk-openstackmon.service
systemctl enable gerenuk-openstackmon.service
```

The service logs are stored in **/var/log/gerenuk-openstackmon.log**.


### 3.3. Openstack configuration (mandatory)
Gerenuk dashboard (openstack-gerenuk-ui) needs to call OpenStack APIs, especially the Keystone and Nova ones.

First, create the **project_manager** role:
```bash
openstack role create project_manager
```

In **/etc/keystone/policy.json**, configure the following rules:
```json
    "project_manager": "role:project_manager",
    "identity:get_user": "rule:admin_or_owner or rule:project_manager",
```

In **/etc/nova/policy.json**, configure the following rules:
```json
    "project_manager": "role:project_manager and project_id:%(project_id)s",
    "default": "rule:admin_or_user or rule:project_manager",
    "os_compute_api:os-hypervisors": "rule:default",
```

And restart the concerned APIs:
```bash
systemctl restart openstack-nova-api.service httpd.service
```






## 4. Install Gerenuk on cloud hypervisors
First of all, follow the previous common prerequisites.

**python3-libvirt** is also needed on hypervisors but already installed by openstack.


### 4.1. Database configuration
Next, configure database in **/etc/gerenuk/gerenuk.conf** (see config reference for details):
```
[database]
db_host = DB_HOST
db_name = gerenuk
db_user = gerenuk
db_pass = *secret*
```


### 4.2. Gerenuk service
Start by installing daemons:
```bash
cp bin/gerenuk-libvirtmon /usr/bin/
cp systemd/gerenuk-libvirtmon.service /usr/lib/systemd/system/
systemctl daemon-reload
```

And finally, start the **gerenuk-libvirtmon** service:
```bash
systemctl start gerenuk-libvirtmon.service
systemctl enable gerenuk-libvirtmon.service
```

The service logs are stored in **/var/log/gerenuk-libvirtmon.log**.
