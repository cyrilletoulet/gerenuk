# Gerenuk update

## Services update
To update the python library, stop all the gerenuk services:
```bash
systemctl snapshot gerenuk-services
systemctl stop gerenuk-*.service
```

Next, upgrade gerenuk from new distribution:
```bash
pip3 install dist/gerenuk-x.y.z.tar.gz
```

And finally restart your services from systemd snapshot:
```bash
systemctl isolate gerenuk-services.snapshot
systemctl delete gerenuk-services.snapshot
```


## Database update
To update the database, run the DB wizard (credentials needs to be configured in **/etc/gerenuk/gerenuk.conf**):
```bash
./bin/gerenuk-db-wizard -c /etc/gerenuk/gerenuk.conf
```
