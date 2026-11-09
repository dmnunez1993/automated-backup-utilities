from typing import Dict, Any

from .docker import DockerInput
from .local import LocalInput
from .kubernetes import KubernetesInput
from .mysql import MySQLInput
from .postgresql import PostgreSQLInput
from .types import (
    INPUT_TYPE_DOCKER,
    INPUT_TYPE_POSTGRESQL,
    INPUT_TYPE_MYSQL,
    INPUT_TYPE_LOCAL,
    INPUT_TYPE_KUBERNETES,
)


def input_factory(config: Dict[str, Any]):
    input_type = config["type"]
    if input_type == INPUT_TYPE_KUBERNETES:
        kubernetes = config["kubernetes"]
        return KubernetesInput(
            name=config["name"],
            statefulset_name=kubernetes["statefulset_name"],
            path=kubernetes["path"],
            namespace=kubernetes.get("namespace", "default"),
            container=kubernetes.get("container"),
            pod_ordinal=kubernetes.get("pod_ordinal"),
            kubeconfig=kubernetes.get("kubeconfig"),
            context=kubernetes.get("context"),
            timeout_seconds=kubernetes.get("timeout_seconds", 300),
        )

    if input_type == INPUT_TYPE_DOCKER:
        return DockerInput(
            name=config["name"],
            volume_name=config["docker"]["volume_name"],
        )

    if input_type == INPUT_TYPE_POSTGRESQL:
        return PostgreSQLInput(
            name=config["name"],
            host=config["postgresql"]["host"],
            port=config["postgresql"]["port"],
            username=config["postgresql"]["username"],
            password=config["postgresql"]["password"],
            database_name=config["postgresql"]["database_name"],
        )

    if input_type == INPUT_TYPE_MYSQL:
        return MySQLInput(
            name=config["name"],
            host=config["mysql"]["host"],
            port=config["mysql"]["port"],
            username=config["mysql"]["username"],
            password=config["mysql"]["password"],
            database_name=config["mysql"]["database_name"],
        )

    if input_type == INPUT_TYPE_LOCAL:
        return LocalInput(
            name=config["name"],
            path=config["local"]["path"],
        )

    raise NotImplementedError(f"Input of type '{input_type}' not implemented")
