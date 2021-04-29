# Gerenuk configuration

By default, gerenuk daemons will look for configuration in /etc/gerenuk/gerenuk.conf.

Don't forget to restrict rights of each configuration file:
```bash
chmod -R 600 /etc/gerenuk/gerenuk.conf
chmod -R 600 /etc/gerenuk/project.d/*
```


## Main configuration reference
For the main configuration reference, see **config/gerenuk.conf**.


## OpenStack project configuration reference

To monitor an OpenStack project, create a specific configuration file in /etc/gerenuk/project.d.
For more consistency, you can name your configuration files following the convention *domain.project.conf*.

For the project specific configuration reference, see **config/project.d/project-sample.conf**.
