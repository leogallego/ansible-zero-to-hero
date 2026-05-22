"""Unit tests for the webserver role defaults and metadata.

These tests validate that the role's defaults/main.yml and
meta/argument_specs.yml are internally consistent, correctly
structured, and follow project conventions.

No Ansible execution is required — these are pure Python tests
that parse YAML files and check their contents.
"""

import os
import pytest
import yaml

# Paths relative to the collection root
COLLECTION_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROLE_DIR = os.path.join(COLLECTION_ROOT, "roles", "webserver")
DEFAULTS_FILE = os.path.join(ROLE_DIR, "defaults", "main.yml")
VARS_FILE = os.path.join(ROLE_DIR, "vars", "main.yml")
ARGUMENT_SPECS_FILE = os.path.join(ROLE_DIR, "meta", "argument_specs.yml")


@pytest.fixture
def defaults():
    """Load and return the role defaults as a dictionary."""
    with open(DEFAULTS_FILE, "r") as fh:
        return yaml.safe_load(fh)


@pytest.fixture
def internal_vars():
    """Load and return the role internal vars as a dictionary."""
    with open(VARS_FILE, "r") as fh:
        return yaml.safe_load(fh)


@pytest.fixture
def argument_specs():
    """Load and return the argument specs as a dictionary."""
    with open(ARGUMENT_SPECS_FILE, "r") as fh:
        return yaml.safe_load(fh)


# --- Defaults tests ---

class TestWebserverDefaults:
    """Validate defaults/main.yml structure and conventions."""

    def test_defaults_file_exists(self):
        """The defaults file must exist."""
        assert os.path.isfile(DEFAULTS_FILE)

    def test_all_defaults_prefixed(self, defaults):
        """Every key in defaults must start with 'webserver_'."""
        for key in defaults:
            assert key.startswith("webserver_"), (
                f"Variable '{key}' is missing the 'webserver_' prefix"
            )

    def test_port_is_integer(self, defaults):
        """webserver_port must be an integer."""
        assert isinstance(defaults["webserver_port"], int)

    def test_service_enabled_is_boolean(self, defaults):
        """webserver_service_enabled must be a boolean."""
        assert isinstance(defaults["webserver_service_enabled"], bool)

    def test_max_connections_is_integer(self, defaults):
        """webserver_max_connections must be an integer."""
        assert isinstance(defaults["webserver_max_connections"], int)

    def test_document_root_is_absolute_path(self, defaults):
        """webserver_document_root must be an absolute path."""
        assert defaults["webserver_document_root"].startswith("/"), (
            "Document root must be an absolute path"
        )

    def test_expected_defaults_present(self, defaults):
        """All expected default variables must be defined."""
        expected = [
            "webserver_port",
            "webserver_document_root",
            "webserver_server_name",
            "webserver_service_enabled",
            "webserver_max_connections",
        ]
        for var in expected:
            assert var in defaults, f"Missing expected default: {var}"


# --- Internal vars tests ---

class TestWebserverInternalVars:
    """Validate vars/main.yml structure and conventions."""

    def test_vars_file_exists(self):
        """The vars file must exist."""
        assert os.path.isfile(VARS_FILE)

    def test_all_internal_vars_prefixed(self, internal_vars):
        """Every key in vars must start with '__webserver_'."""
        for key in internal_vars:
            assert key.startswith("__webserver_"), (
                f"Variable '{key}' is missing the '__webserver_' prefix"
            )

    def test_packages_default_is_list(self, internal_vars):
        """__webserver_packages_default must be a list."""
        assert isinstance(internal_vars["__webserver_packages_default"], list)


# --- Argument specs tests ---

class TestWebserverArgumentSpecs:
    """Validate meta/argument_specs.yml consistency."""

    def test_argument_specs_file_exists(self):
        """The argument specs file must exist."""
        assert os.path.isfile(ARGUMENT_SPECS_FILE)

    def test_main_entrypoint_exists(self, argument_specs):
        """The 'main' entrypoint must be defined."""
        assert "main" in argument_specs["argument_specs"]

    def test_all_spec_options_prefixed(self, argument_specs):
        """Every option in the spec must start with 'webserver_'."""
        options = argument_specs["argument_specs"]["main"].get("options", {})
        for key in options:
            assert key.startswith("webserver_"), (
                f"Argument spec option '{key}' is missing the "
                "'webserver_' prefix"
            )

    def test_defaults_covered_by_specs(self, defaults, argument_specs):
        """Every variable in defaults must have an argument spec entry."""
        options = argument_specs["argument_specs"]["main"].get("options", {})
        for key in defaults:
            assert key in options, (
                f"Default variable '{key}' has no matching argument spec"
            )
