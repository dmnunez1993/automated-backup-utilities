from datetime import datetime, timezone
import json
import logging
import os
import shutil
import subprocess
from tempfile import mkdtemp
from typing import Optional

from .base import BaseInput


class KubernetesInput(BaseInput):
    """Archive a mounted directory from one StatefulSet replica."""

    def __init__(
        self,
        name: str,
        statefulset_name: str,
        path: str,
        namespace: str = "default",
        container: Optional[str] = None,
        pod_ordinal: Optional[int] = None,
        kubeconfig: Optional[str] = None,
        context: Optional[str] = None,
        timeout_seconds: int = 300,
    ):
        super().__init__(name)
        if not statefulset_name or not namespace:
            raise ValueError("statefulset_name and namespace must not be empty")
        if not isinstance(path, str) or not path.startswith("/"):
            raise ValueError("Kubernetes backup path must be an absolute directory path")
        if pod_ordinal is not None and (
            type(pod_ordinal) is not int or pod_ordinal < 0
        ):
            raise ValueError("pod_ordinal must be a non-negative integer")
        if type(timeout_seconds) is not int or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive integer")
        self._statefulset_name = statefulset_name
        self._path = path
        self._namespace = namespace
        self._container = container
        self._pod_ordinal = pod_ordinal
        self._kubeconfig = kubeconfig
        self._context = context
        self._timeout_seconds = timeout_seconds
        self._logger = logging.getLogger("automated_backup_utilities")

    def backup(self) -> str:
        command = ["kubectl", f"--namespace={self._namespace}"]
        if self._kubeconfig:
            command.append(f"--kubeconfig={self._kubeconfig}")
        if self._context:
            command.append(f"--context={self._context}")

        result = subprocess.run(
            command + ["get", f"statefulset/{self._statefulset_name}", "-o", "json"],
            stdout=subprocess.PIPE,
            text=True,
            check=True,
            timeout=self._timeout_seconds,
        )
        spec = json.loads(result.stdout)["spec"]
        start = spec.get("ordinals", {}).get("start", 0)
        ordinal = start if self._pod_ordinal is None else self._pod_ordinal
        if not start <= ordinal < start + spec.get("replicas", 1):
            raise ValueError("Selected pod ordinal is outside the StatefulSet replica range")

        pod = f"{self._statefulset_name}-{ordinal}"
        exec_command = command + ["exec", f"pod/{pod}"]
        if self._container:
            exec_command.append(f"--container={self._container}")
        exec_command += ["--", "tar", "czf", "-", "-C", self._path, "."]

        self._logger.info("Backing up %s from Kubernetes pod %s/%s",
                          self._path, self._namespace, pod)
        output_folder = mkdtemp()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H:%M:%S")
        output_path = os.path.join(output_folder, f"{self.get_name()}_{now_str}.tar.gz")
        try:
            # No shell or TTY: stdout is the binary archive, stderr stays separate.
            with open(output_path, "wb") as archive:
                subprocess.run(
                    exec_command,
                    stdout=archive,
                    check=True,
                    timeout=self._timeout_seconds,
                )
        except Exception:
            shutil.rmtree(output_folder)
            raise

        self._logger.info("Finished backing up Kubernetes pod %s/%s",
                          self._namespace, pod)
        return output_path
