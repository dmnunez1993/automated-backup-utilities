import importlib.machinery
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml


loader = importlib.machinery.SourceFileLoader(
    'backup_deployer', str(Path(__file__).resolve().parents[1] / 'deployer'))
spec = importlib.util.spec_from_loader(loader.name, loader)
deployer = importlib.util.module_from_spec(spec)
loader.exec_module(deployer)


class DeployerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'config.yaml'
        self.generated_config = self.root / 'config.docker.yaml'
        self.override = self.root / deployer.OVERRIDE_FILE
        self.environment = patch.dict(os.environ, {'HOME': str(self.root)}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.output_patch = patch.object(deployer, 'DOCKER_CONFIG_PATH',
                                         str(self.generated_config))
        self.output_patch.start()
        self.addCleanup(self.output_patch.stop)

    def kubeconfig(self, relative='.kube/config'):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('apiVersion: v1\n')
        return path

    def generate(self, configs):
        self.config.write_text(yaml.safe_dump(configs))
        return deployer.generate_override(str(self.root), str(self.config))

    def service(self):
        return yaml.safe_load(self.override.read_text())['services']['backup_utilities']

    def backups(self):
        return yaml.safe_load(self.generated_config.read_text())

    def kubernetes(self, **options):
        return {'name': 'volume', 'type': 'kubernetes', 'kubernetes': {
            'statefulset_name': 'files', 'path': '/data', **options}}

    def test_default_config_mount_is_read_only(self):
        path = self.kubeconfig()
        self.assertTrue(self.generate([self.kubernetes()]))
        service = self.service()
        self.assertEqual(service['environment']['KUBECONFIG'], '/kube/0/config')
        self.assertEqual(service['volumes'], [{
            'type': 'bind', 'source': str(path.parent), 'target': '/kube/0',
            'read_only': True, 'bind': {'create_host_path': False}}])

    def test_exported_directory_and_changed_directory_are_picked_up(self):
        for directory in ['first', 'second']:
            path = self.kubeconfig(f'{directory}/config')
            os.environ['KUBE_CONFIG_DIR'] = str(path.parent)
            self.generate([self.kubernetes()])
            self.assertEqual(self.service()['volumes'][0]['source'], str(path.parent))

    def test_kubeconfig_list_preserves_order(self):
        paths = [self.kubeconfig('one/cluster'), self.kubeconfig('two/config')]
        os.environ['KUBECONFIG'] = os.pathsep.join(str(path) for path in paths)
        self.generate([self.kubernetes()])
        self.assertEqual(self.service()['environment']['KUBECONFIG'],
                         '/kube/0/cluster:/kube/1/config')

    def test_explicit_host_config_takes_precedence_and_is_remapped(self):
        self.kubeconfig('credentials/cluster')
        os.environ['KUBE_CONFIG_DIR'] = '/does/not/exist'
        backup = self.kubernetes(kubeconfig='credentials/cluster', context='production')
        self.generate([backup])
        generated = self.backups()[0]['kubernetes']
        self.assertEqual(generated['kubeconfig'], '/kube/0/cluster')
        self.assertEqual(generated['context'], 'production')
        self.assertEqual(yaml.safe_load(self.config.read_text()), [backup])

    def test_directory_setting_takes_precedence_over_kubeconfig_env(self):
        self.kubeconfig('chosen/config')
        os.environ.update(KUBE_CONFIG_DIR='chosen', KUBECONFIG='/missing')
        self.generate([self.kubernetes()])
        self.assertEqual(self.service()['volumes'][0]['source'], str(self.root / 'chosen'))

    def test_same_directory_is_only_mounted_once(self):
        first = self.kubeconfig('credentials/first')
        second = self.kubeconfig('credentials/second')
        self.generate([self.kubernetes(kubeconfig=str(first)),
                       self.kubernetes(kubeconfig=str(second))])
        self.assertEqual(len(self.service()['volumes']), 1)
        self.assertEqual(self.backups()[1]['kubernetes']['kubeconfig'], '/kube/0/second')

    def test_local_and_kubernetes_inputs_work_together(self):
        self.kubeconfig()
        self.generate([{'type': 'local', 'name': 'files', 'local': {'path': '/data'}},
                       self.kubernetes()])
        self.assertEqual(len(self.service()['volumes']), 2)
        self.assertEqual(self.backups()[0]['local']['path'], '/local_inputs/files')

    def test_missing_config_fails_before_writing_override(self):
        with self.assertRaises(FileNotFoundError):
            self.generate([self.kubernetes()])
        self.assertFalse(self.override.exists())
        self.assertFalse(self.generated_config.exists())

    def test_no_kubernetes_input_needs_no_kubeconfig(self):
        self.assertFalse(self.generate([{'type': 'mysql'}]))
        self.assertFalse(self.override.exists())

    def test_removing_inputs_removes_generated_override(self):
        self.kubeconfig()
        self.generate([self.kubernetes()])
        self.assertFalse(self.generate([{'type': 'mysql'}]))
        self.assertFalse(self.override.exists())

    def test_unrelated_override_is_preserved(self):
        self.override.write_text('services: {}\n')
        self.assertFalse(self.generate([{'type': 'mysql'}]))
        self.assertTrue(self.override.exists())

    def test_main_loads_dotenv_but_exported_env_takes_precedence(self):
        first = self.kubeconfig('dotenv/config')
        second = self.kubeconfig('direnv/config')
        (self.root / '.env').write_text(f'KUBE_CONFIG_DIR={first.parent}\n')
        self.config.write_text(yaml.safe_dump([self.kubernetes()]))
        with patch.object(deployer, 'get_repo_root', return_value=str(self.root)), \
             patch.object(deployer, 'run_command') as run, \
             patch('sys.argv', ['deployer', 'deploy']):
            deployer.main()
            self.assertEqual(self.service()['volumes'][0]['source'], str(first.parent))
            os.environ['KUBE_CONFIG_DIR'] = str(second.parent)
            deployer.main()
            self.assertEqual(self.service()['volumes'][0]['source'], str(second.parent))
            self.assertEqual(run.call_count, 2)


if __name__ == '__main__':
    unittest.main()
