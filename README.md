# Automated Backup Utilities

App for automating the backup of different types of data sources.

Supported Data Sources:

- MySQL Databases
- PostgreSQL Databases
- Docker Volumes
- Local directories
- Kubernetes StatefulSet volume data (a mounted directory from one replica)

Supported Backup Storage outputs:

- [MinIO](https://min.io/)

### Dependencies

- [python](https://www.postgresql.org/) - Used for developing the app
- [postgresql](https://www.postgresql.org/) - Mainly for using pg_dump to backup databases
- [mysql](https://www.mysql.com/) - Mainly for using pg_dump to backup databases
- [docker](https://www.docker.com/) - Used to backup docker volumes and for deployment
- [kubectl](https://kubernetes.io/docs/tasks/tools/) - Required for Kubernetes volume backups; included in the Docker image

### Kubernetes volume backups

Use `type: kubernetes` to archive files from a directory mounted in a StatefulSet
container. Set `statefulset_name` and the absolute `path` inside the container in
the `kubernetes` configuration block (see `config.yaml.sample`). The resulting
`.tar.gz` contains that directory's contents and is sent to the configured outputs.

Optional settings:

- `namespace`: defaults to `default`.
- `container`: container that mounts the volume; if omitted, kubectl uses the pod's default container annotation or first container.
- `pod_ordinal`: selects a replica by its ordinal. Defaults to the StatefulSet's starting ordinal, usually `0`. Configure separate backups for replicas with distinct data.
- `kubeconfig` and `context`: use a specific kubeconfig file and cluster context. Otherwise kubectl uses its normal authentication, including an in-cluster service account.
- `timeout_seconds`: maximum duration of each kubectl command, defaults to `300`.

The selected container must be running and have `tar` with gzip support installed.
The Kubernetes identity needs `get` on `statefulsets` in API group `apps`, `get`
on `pods`, and `create` on `pods/exec` in the core API group, in the target namespace.
With `./deployer start` or `./deployer deploy`, Kubernetes inputs automatically
get read-only kubeconfig directory mounts and container paths. The deployer uses,
in order, the input's explicit `kubeconfig` host file, `KUBE_CONFIG_DIR/config`,
the files in `KUBECONFIG`, or `~/.kube/config`. Multiple `KUBECONFIG` files retain
their merge order. Relative host paths are resolved against the repository root.

For example, add this to `.env`:

```dotenv
KUBE_CONFIG_DIR=/home/you/.kube
```

Or export it from a direnv-managed `.envrc`:

```bash
export KUBE_CONFIG_DIR="$HOME/.kube"
```

The deployer reads `.env` automatically; existing shell variables take precedence.
For `.envrc`, use direnv with its shell hook and run `direnv allow` before deploying.
The deployer does not execute `.envrc` itself. Leave `kubeconfig` out of the backup
YAML to use the environment/default selection. Your original backup YAML is not
modified; container paths are written to the generated Docker configuration.
After changing the path in `.envrc`, let direnv reload it (run `direnv allow` if
prompted), then run `./deployer deploy` again to regenerate the container mounts.
You can also export `KUBECONFIG=/path/to/config` instead of `KUBE_CONFIG_DIR`.

Mounting the directory preserves relative certificate paths inside it. Credentials
referenced by absolute paths or outside that directory need additional mounts,
and kubeconfig authentication plugins must be installed in the image. When using
Docker without the deployer, configure those mounts and container paths yourself.

This copies live files from the selected mounted path; it does not create a PVC
snapshot or back up StatefulSet manifests. Pause writes or use an application
backup procedure when consistency matters. For running MySQL or PostgreSQL
databases, use the existing database inputs for logical dumps rather than copying
their live data directories.

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
