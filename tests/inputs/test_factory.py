import pytest

from inputs.factory import input_factory
from inputs.docker import DockerInput
from inputs.local import LocalInput
from inputs.mysql import MySQLInput
from inputs.postgresql import PostgreSQLInput


def test_postgresql_type_returns_postgresql_input():
    config = {
        "name": "pg_backup",
        "type": "postgresql",
        "postgresql": {
            "host": "localhost",
            "port": 5432,
            "username": "user",
            "password": "pass",
            "database_name": "mydb",
        },
    }
    assert isinstance(input_factory(config), PostgreSQLInput)


def test_mysql_type_returns_mysql_input():
    config = {
        "name": "mysql_backup",
        "type": "mysql",
        "mysql": {
            "host": "localhost",
            "port": 3306,
            "username": "user",
            "password": "pass",
            "database_name": "mydb",
        },
    }
    assert isinstance(input_factory(config), MySQLInput)


def test_docker_type_returns_docker_input():
    config = {
        "name": "docker_backup",
        "type": "docker",
        "docker": {
            "volume_name": "myvolume"
        },
    }
    assert isinstance(input_factory(config), DockerInput)


def test_local_type_returns_local_input():
    config = {
        "name": "local_backup",
        "type": "local",
        "local": {
            "path": "/some/path"
        },
    }
    assert isinstance(input_factory(config), LocalInput)


def test_unknown_type_raises_not_implemented():
    config = {"name": "x", "type": "ftp"}
    with pytest.raises(NotImplementedError):
        input_factory(config)
