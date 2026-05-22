"""pytest configuration for parasoltech.infrastructure collection tests.

This conftest.py sets up the environment so pytest-ansible can locate
the collection's modules and plugins.  It runs before any test is
collected, ensuring Ansible sees the correct paths.
"""

import os

# Absolute path to this tests/ directory
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Collection root (one level up from tests/)
PROJECT_ROOT = os.path.dirname(TESTS_DIR)

# Point Ansible at the plugins/modules directory so modules can be
# invoked by short name through the ansible_module fixture.
MODULES_PATH = os.path.join(PROJECT_ROOT, "plugins", "modules")
os.environ.setdefault("ANSIBLE_LIBRARY", MODULES_PATH)

# Point Ansible at the editable-install symlink tree created by
# `ade install -e .` so FQCNs resolve correctly.
COLLECTIONS_PATH = os.path.join(PROJECT_ROOT, "collections")
os.environ.setdefault("ANSIBLE_COLLECTIONS_PATH", COLLECTIONS_PATH)
