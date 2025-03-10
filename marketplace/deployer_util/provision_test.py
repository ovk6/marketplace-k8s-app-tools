#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import provision
from provision import dns1123_name
from provision import limit_name

import config_helper


class ProvisionTest(unittest.TestCase):

  def test_dns1123_name(self):
    self.assertEqual(dns1123_name('valid-name'), 'valid-name')
    self.assertEqual(dns1123_name('aA'), 'aa')
    self.assertEqual(
        dns1123_name('*sp3cial-@chars.(rem0ved^'), 'sp3cial-chars-rem0ved')
    self.assertEqual(dns1123_name('-abc.def.'), 'abc-def')
    self.assertEqual(dns1123_name('-123.456.'), '123-456')
    self.assertModifiedName(
        dns1123_name('Lorem-Ipsum-is-simply-dummy-text-of-the-printing-and-'
                     'typesettings-----------------------------------------'),
        'lorem-ipsum-is-simply-dummy-text-of-the-printing-and-typese')
    self.assertModifiedName(
        dns1123_name('Lorem-Ipsum-is-simply-dummy-text-of-the-printing-and-'
                     'typesettings.........................................'),
        'lorem-ipsum-is-simply-dummy-text-of-the-printing-and-typese')

  def test_limit_name(self):
    self.assertEqual(limit_name('valid-name'), 'valid-name')
    self.assertEqual(limit_name('valid-name', 8), 'val-030a')

  def assertModifiedName(self, text, expected):
    self.assertEqual(text[:-5], expected)
    self.assertRegexpMatches(text[-5:], r'-[a-f0-9]{4}')

  def assertListElementsEqual(self, list1, list2):
    return self.assertEqual(sorted(list1), sorted(list2))

  def test_deployer_image_inject(self):
    schema = config_helper.Schema.load_yaml('''
    properties:
      deployer_image:
        type: string
        x-google-marketplace:
          type: DEPLOYER_IMAGE
    ''')
    values = {}
    deployer_image = 'gcr.io/cloud-marketplace/partner/solution/deployer:latest'
    self.assertEquals(
        provision.inject_deployer_image_properties(values, schema,
                                                   deployer_image),
        {"deployer_image": deployer_image})

  def test_deployer_image_to_repo_prefix(self):
    self.assertEqual(
        'gcr.io/test',
        provision.deployer_image_to_repo_prefix('gcr.io/test/deployer'))
    self.assertEqual(
        'gcr.io/test',
        provision.deployer_image_to_repo_prefix('gcr.io/test/deployer:0.1.1'))
    self.assertEqual(
        'gcr.io/test',
        provision.deployer_image_to_repo_prefix(
            'gcr.io/test/deployer@sha256:0123456789abcdef'))
    with self.assertRaises(Exception):
      provision.deployer_image_to_repo_prefix('gcr.io/test/test')
    with self.assertRaises(Exception):
      provision.deployer_image_to_repo_prefix(
          'gcr.io/test/test@sha256:0123456789abcdef')
    with self.assertRaises(Exception):
      provision.deployer_image_to_repo_prefix('gcr.io/test/test:0.1.1')

  def test_make_deployer_rolebindings_no_roles(self):
    schema = config_helper.Schema.load_yaml("""
        x-google-marketplace:
          # v2 required fields
          schemaVersion: v2
          applicationApiVersion: v1beta1
          publishedVersion: 0.0.1
          publishedVersionMetadata:
            releaseNote: Initial release
            recommended: True
          images: {}

        properties:
          simple:
            type: string
      """)
    self.assertEquals(
        [
            # The default namespace rolebinding should be created
            {
                'apiVersion':
                    'rbac.authorization.k8s.io/v1',
                'kind':
                    'RoleBinding',
                'metadata': {
                    'name': 'app-name-1:deployer-rb',
                    'namespace': 'namespace-1',
                    'labels': {
                        'some-key': 'some-value'
                    },
                },
                'roleRef': {
                    'apiGroup': 'rbac.authorization.k8s.io',
                    # Note: predefined ones are actually cluster roles.
                    'kind': 'ClusterRole',
                    'name': 'cluster-admin',
                },
                'subjects': [{
                    'kind': 'ServiceAccount',
                    'name': 'app-name-deployer-sa',
                    'namespace': 'namespace-1',
                }],
            },
        ],
        provision.make_deployer_rolebindings(schema, 'namespace-1',
                                             'app-name-1',
                                             {'some-key': 'some-value'},
                                             'app-name-deployer-sa'))

  def test_make_deployer_rolebindings_all_roles(self):
    schema = config_helper.Schema.load_yaml("""
        x-google-marketplace:
          # v2 required fields
          schemaVersion: v2
          applicationApiVersion: v1beta1
          publishedVersion: 0.0.1
          publishedVersionMetadata:
            releaseNote: Initial release
            recommended: True
          images: {}

          deployerServiceAccount:
            roles:
            - type: Role
              rulesType: CUSTOM
              rules:
              - apiGroups: ['apps/v1']
                resources: ['Deployment']
                verbs: ['*']
            - type: ClusterRole
              rulesType: CUSTOM
              rules:
              - apiGroups: ['v1']
                resources: ['Secret']
                verbs: ['*']
            - type: Role
              rulesType: PREDEFINED
              rulesFromRoleName: edit
            - type: ClusterRole
              rulesType: PREDEFINED
              rulesFromRoleName: cluster-admin
        properties:
          simple:
            type: string
      """)
    self.assertListElementsEqual(
        [
            {
                'apiVersion':
                    'rbac.authorization.k8s.io/v1',
                'kind':
                    'Role',
                'metadata': {
                    'name': 'app-name-1:deployer-r0',
                    'namespace': 'namespace-1',
                    'labels': {
                        'some-key': 'some-value'
                    },
                },
                'rules': [{
                    'apiGroups': ['apps/v1'],
                    'resources': ['Deployment'],
                    'verbs': ['*'],
                }],
            },
            {
                'apiVersion':
                    'rbac.authorization.k8s.io/v1',
                'kind':
                    'RoleBinding',
                'metadata': {
                    'name': 'app-name-1:deployer-rb0',
                    'namespace': 'namespace-1',
                    'labels': {
                        'some-key': 'some-value'
                    },
                },
                'roleRef': {
                    'apiGroup': 'rbac.authorization.k8s.io',
                    'kind': 'Role',
                    'name': 'app-name-1:deployer-r0',
                },
                'subjects': [{
                    'kind': 'ServiceAccount',
                    'name': 'app-name-deployer-sa',
                    'namespace': 'namespace-1',
                }]
            },
            {
                'apiVersion':
                    'rbac.authorization.k8s.io/v1',
                'kind':
                    'ClusterRole',
                'metadata': {
                    'name': 'namespace-1:app-name-1:deployer-cr0',
                    'labels': {
                        'some-key': 'some-value'
                    },
                },
                'rules': [{
                    'apiGroups': ['v1'],
                    'resources': ['Secret'],
                    'verbs': ['*'],
                }],
            },
            {
                'apiVersion':
                    'rbac.authorization.k8s.io/v1',
                'kind':
                    'ClusterRoleBinding',
                'metadata': {
                    'name': 'namespace-1:app-name-1:deployer-crb0',
                    'labels': {
                        'some-key': 'some-value'
                    },
                },
                'roleRef': {
                    'apiGroup': 'rbac.authorization.k8s.io',
                    'kind': 'ClusterRole',
                    'name': 'namespace-1:app-name-1:deployer-cr0',
                },
                'subjects': [{
                    'kind': 'ServiceAccount',
                    'name': 'app-name-deployer-sa',
                    'namespace': 'namespace-1',
                }],
            },
            {
                'apiVersion':
                    'rbac.authorization.k8s.io/v1',
                'kind':
                    'RoleBinding',
                'metadata': {
                    'name': 'app-name-1:edit:deployer-rb',
                    'namespace': 'namespace-1',
                    'labels': {
                        'some-key': 'some-value'
                    },
                },
                'roleRef': {
                    'apiGroup': 'rbac.authorization.k8s.io',
                    # Note: predefined ones are actually cluster roles.
                    'kind': 'ClusterRole',
                    'name': 'edit',
                },
                'subjects': [{
                    'kind': 'ServiceAccount',
                    'name': 'app-name-deployer-sa',
                    'namespace': 'namespace-1',
                }],
            },
            {
                'apiVersion':
                    'rbac.authorization.k8s.io/v1',
                'kind':
                    'ClusterRoleBinding',
                'metadata': {
                    'name': 'namespace-1:app-name-1:cluster-admin:deployer-crb',
                    'labels': {
                        'some-key': 'some-value'
                    },
                },
                'roleRef': {
                    'apiGroup': 'rbac.authorization.k8s.io',
                    'kind': 'ClusterRole',
                    'name': 'cluster-admin',
                },
                'subjects': [{
                    'kind': 'ServiceAccount',
                    'name': 'app-name-deployer-sa',
                    'namespace': 'namespace-1',
                }],
            }
        ],
        provision.make_deployer_rolebindings(schema, 'namespace-1',
                                             'app-name-1',
                                             {'some-key': 'some-value'},
                                             'app-name-deployer-sa'))

  def test_make_deployer_rolebindings_clusterrole_only(self):
    schema = config_helper.Schema.load_yaml("""
        x-google-marketplace:
          # v2 required fields
          schemaVersion: v2
          applicationApiVersion: v1beta1
          publishedVersion: 0.0.1
          publishedVersionMetadata:
            releaseNote: Initial release
            recommended: True
          images: {}

          deployerServiceAccount:
            roles:
            - type: ClusterRole
              rulesType: PREDEFINED
              rulesFromRoleName: cluster-admin
        properties:
          simple:
            type: string
      """)
    self.assertListElementsEqual(
        [
            # The default namespace rolebinding should also be created
            {
                'apiVersion':
                    'rbac.authorization.k8s.io/v1',
                'kind':
                    'RoleBinding',
                'metadata': {
                    'name': 'app-name-1:deployer-rb',
                    'namespace': 'namespace-1',
                    'labels': {
                        'some-key': 'some-value'
                    },
                },
                'roleRef': {
                    'apiGroup': 'rbac.authorization.k8s.io',
                    # Note: predefined ones are actually cluster roles.
                    'kind': 'ClusterRole',
                    'name': 'cluster-admin',
                },
                'subjects': [{
                    'kind': 'ServiceAccount',
                    'name': 'app-name-deployer-sa',
                    'namespace': 'namespace-1',
                }],
            },
            {
                'apiVersion':
                    'rbac.authorization.k8s.io/v1',
                'kind':
                    'ClusterRoleBinding',
                'metadata': {
                    'name': 'namespace-1:app-name-1:cluster-admin:deployer-crb',
                    'labels': {
                        'some-key': 'some-value'
                    },
                },
                'roleRef': {
                    'apiGroup': 'rbac.authorization.k8s.io',
                    'kind': 'ClusterRole',
                    'name': 'cluster-admin',
                },
                'subjects': [{
                    'kind': 'ServiceAccount',
                    'name': 'app-name-deployer-sa',
                    'namespace': 'namespace-1',
                }],
            }
        ],
        provision.make_deployer_rolebindings(schema, 'namespace-1',
                                             'app-name-1',
                                             {'some-key': 'some-value'},
                                             'app-name-deployer-sa'))
