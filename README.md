# Automated Backup Utilities

App for automating the backup of different types of data sources.

Supported Data Sources:

- MySQL Databases
- PostgreSQL Databases
- Docker Volumes

Supported Backup Storage outputs:

- [MinIO](https://min.io/)

### Dependencies

- [python](https://www.postgresql.org/) - Used for developing the app
- [postgresql](https://www.postgresql.org/) - Mainly for using pg_dump to backup databases
- [mysql](https://www.mysql.com/) - Mainly for using pg_dump to backup databases
- [docker](https://www.docker.com/) - Used to backup docker volumes and for deployment

### Development

Make sure previously mentioned dependencies are installed.

To install the app's dependencies:

    pip install -r requirements.txt

Ensure that a .env file is set up. You can use the example provided in this repository (.env.example) as a template, but the path can be configured to any relative or absolute location as needed:

    cp .env.example .env

Additionally, it is required to set up a YAML configuration file. It is possible to use the example provided in this repository (config.yaml.sample) as a starting point, but make sure to customize it according to each backup's specific parameters:

    cp config.yaml.sample config.yaml

To run the app:

    python3 app.py

### Testing

To run the unit tests:

    python -m pytest tests/ -v

### Deployment

To build the project for deployment using docker:

    ./deployer build

In the same way as in the development section, both .env and config.yaml files should be configured.

To start the container:

    ./deployer start

To stop the container:

    ./deployer stop

To start the container and keep it running in the background:

    ./deployer deploy
