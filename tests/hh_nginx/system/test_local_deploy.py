"""Local-only (intranet) nginx deploys: which domains count as local, the allow list, and the
generated config (hh_nginx/deploy/deploy_helpers_nginx.py, deploy_hooks.py, http/nginx_config_helpers.py).

Regression: the hookified deploy only treated 192.168/10/172.16 IP domains as local, so a
`foxhouse.local` install got a public config with no allow/deny rules, and it ignored the
install config's local_allow_block.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict

import pytest

import hh_nginx.deploy.deploy_helpers_nginx as nginx_helpers
import hh_nginx.deploy.deploy_hooks as nginx_hooks
import hh_nginx.deploy.http.nginx_config_helpers as config_helpers
from hh_nginx.deploy.deploy_helpers_nginx import (
    DEFAULT_LOCAL_ALLOW_BLOCK, get_local_settings, is_local_domain,
)
from hh_nginx.deploy.http.nginx_config_helpers import (
    get_client_ip_access_control, normalize_allow_ranges,
)


# ---------- is_local_domain ----------

@pytest.mark.parametrize("domain", [
    "foxhouse.local", "FOXHOUSE.LOCAL", "foxhouse.local.", "admin.foxhouse.local",
    "localhost", "app.localhost", "127.0.0.1",
    "192.168.1.100", "10.0.0.5", "172.16.0.1", "172.31.255.254", "fd00::1",
])
def test_local_domains(domain: str) -> None:
    assert is_local_domain(domain)


@pytest.mark.parametrize("domain", [
    "", "example.com", "foxhouse.ai", "local.example.com", "notlocal",
    "8.8.8.8", "172.15.0.1", "172.32.0.1", "192.0.2.10", "169.254.1.1", "2001:db8::1",
])
def test_public_domains(domain: str) -> None:
    assert not is_local_domain(domain)


# ---------- get_local_settings ----------

def test_dot_local_uses_configured_allow_block() -> None:
    sec = {"domain": "foxhouse.local", "local_allow_block": "192.168.1.0/24,10.0.0.0/8"}
    assert get_local_settings(sec) == (True, "192.168.1.0/24,10.0.0.0/8")


def test_missing_allow_block_falls_back_to_private_ranges() -> None:
    assert get_local_settings({"domain": "foxhouse.local"}) == (True, DEFAULT_LOCAL_ALLOW_BLOCK)
    assert get_local_settings({"domain": "foxhouse.local", "local_allow_block": "  "}) == (True, DEFAULT_LOCAL_ALLOW_BLOCK)


def test_allow_block_is_not_derived_from_a_hostname() -> None:
    _, block = get_local_settings({"domain": "foxhouse.local"})
    assert "foxhouse" not in block


def test_public_domain_has_no_allow_block() -> None:
    assert get_local_settings({"domain": "example.com", "local_allow_block": "192.168.1.0/24"}) == (False, "")


@pytest.mark.parametrize("value", ["1", "true", "Yes", "on"])
def test_local_only_forces_local(value: str) -> None:
    sec = {"domain": "intranet.example.com", "local_only": value, "local_allow_block": "192.168.5.0/24"}
    assert get_local_settings(sec) == (True, "192.168.5.0/24")


@pytest.mark.parametrize("value", ["0", "false", "No", "off"])
def test_local_only_off_forces_public(value: str) -> None:
    assert get_local_settings({"domain": "foxhouse.local", "local_only": value}) == (False, "")


@pytest.mark.parametrize("value", ["", "maybe"])
def test_empty_or_invalid_local_only_detects_from_domain(value: str) -> None:
    assert get_local_settings({"domain": "foxhouse.local", "local_only": value})[0] is True
    assert get_local_settings({"domain": "example.com", "local_only": value})[0] is False


# ---------- allow list normalization ----------

@pytest.mark.parametrize("raw, expected", [
    ("192.168.1.0/24,10.0.0.0/8", ["192.168.1.0/24", "10.0.0.0/8"]),
    ("192.168.1.", ["192.168.1.0/24"]),            # old install config default
    ("10.", ["10.0.0.0/8"]),
    ("172.16.", ["172.16.0.0/16"]),
    ("192.168.1.7", ["192.168.1.7"]),
    ("192.168.1.7/24", ["192.168.1.0/24"]),
    ("fd00::/8, ::1", ["fd00::/8", "::1"]),
    (" 10.0.0.0/8 ,, 10.0.0.0/8 ", ["10.0.0.0/8"]),
    ("foxhouse, 999.1.1.1, 192.168.1.0/33, 1.2.3.4.5", []),
    ("", []),
])
def test_normalize_allow_ranges(raw: str, expected: list) -> None:
    assert normalize_allow_ranges(raw) == expected


def test_access_control_always_allows_localhost_and_ends_with_deny_all() -> None:
    lines = [l.strip() for l in get_client_ip_access_control("192.168.1.") if l.strip()]
    assert lines[1:] == ["allow 127.0.0.1;", "allow 192.168.1.0/24;", "deny all;"]


def test_access_control_with_only_bad_entries_still_denies() -> None:
    lines = [l.strip() for l in get_client_ip_access_control("not-an-ip") if l.strip()]
    assert lines[1:] == ["allow 127.0.0.1;", "deny all;"]


# ---------- generated config ----------

@pytest.fixture
def stub_install(monkeypatch):
    """Config generators read the install config, the static whitelist and the misc whitelist."""
    monkeypatch.setattr(config_helpers, "_load_flask_start_port", lambda project: 5001)
    import hh.deploy.install_helpers_config as install_config
    monkeypatch.setattr(install_config, "load_install_config", lambda project: {
        "webroot_dir": "/var/www/html", "htpasswd_dir": "/var/www", "htaccess_guest_password": "",
    })
    import hh_nginx.deploy.http.nginx_whitelist as whitelist
    monkeypatch.setattr(whitelist, "generate_nginx_static_locations",
                        lambda project: {"config": "location /js/ {\n    alias /srv/x/site/js/;\n}"})
    import hh.deploy.deploy_utils as deploy_utils
    monkeypatch.setattr(deploy_utils, "load_whitelist_with_extensions", lambda *a, **k: [])


def _server_blocks(config: str) -> list:
    return re.findall(r"^server \{\n(.*?)^\}", config, re.MULTILINE | re.DOTALL)


def _assert_local_block(block: str) -> None:
    assert "allow 192.168.1.0/24;" in block
    assert "deny all;" in block
    assert re.search(r"listen \d", block) is None or "listen 80;" in block or "listen 443 ssl http2;" in block
    assert not re.search(r"listen \d+\.\d+\.\d+\.\d+:", block), "local sites must not bind to an IP"


def _assert_acme_open(block: str) -> None:
    m = re.search(r"location \^~ /\.well-known/acme-challenge/ \{(.*?)\}", block, re.DOTALL)
    assert m, "port-80 block needs the ACME location"
    assert "allow all;" in m.group(1)
    assert "auth_basic off;" in m.group(1)


def test_local_http_config_for_dot_local(stub_install) -> None:
    config = nginx_helpers.create_nginx_config_local("foxhouse.local", "foxhouse", "192.168.1.")
    blocks = _server_blocks(config)
    assert len(blocks) == 3
    for block in blocks:
        _assert_local_block(block)
        _assert_acme_open(block)
        assert "listen 80;" in block
    assert "server_name foxhouse.local www.foxhouse.local;" in config


def test_local_https_config_for_dot_local(stub_install) -> None:
    config = nginx_helpers.create_nginx_ssl_config_local(
        "foxhouse.local", "foxhouse", "192.168.1.0/24", "/etc/nginx/ssl/foxhouse.local")
    blocks = _server_blocks(config)
    assert len(blocks) == 4
    redirect, *https = blocks
    _assert_local_block(redirect)
    _assert_acme_open(redirect)
    assert "listen 80;" in redirect
    for block in https:
        _assert_local_block(block)
        assert "listen 443 ssl http2;" in block


# ---------- deploy_85 hook end to end (files in a temp dir) ----------

def _run_deploy_85(tmp_path: Path, monkeypatch, install: Dict[str, str]) -> dict:
    cfg = tmp_path / "install.cnf"
    cfg.write_text("[install]\n" + "".join(f"{k} = {v}\n" for k, v in install.items()))
    nginx_root = tmp_path / "nginx"
    (nginx_root / "sites-available").mkdir(parents=True)
    (nginx_root / "sites-enabled").mkdir(parents=True)

    import hh.deploy.deploy_utils as deploy_utils
    import hh.deploy.install_helpers_config as install_config
    import hh.gateway.gateway as gateway_mod
    monkeypatch.setattr(deploy_utils, "detect_project_context", lambda: ("foxhouse", tmp_path))
    monkeypatch.setattr(install_config, "get_install_config_path", lambda project: cfg)
    monkeypatch.setattr(gateway_mod, "get_gateway", lambda: None)
    monkeypatch.setattr(nginx_helpers, "get_server_ip", lambda: "203.0.113.5")

    real_path = Path

    def fake_path(*parts):
        p = real_path(*parts)
        s = str(p)
        if s.startswith("/etc/nginx/"):
            return nginx_root / s[len("/etc/nginx/"):]
        return p

    monkeypatch.setattr(nginx_hooks, "Path", fake_path)
    result = nginx_hooks.deploy_nginx_config()
    result["_config"] = (nginx_root / "sites-available" / install["domain"]).read_text() \
        if result.get("config_written") else ""
    return result


def test_deploy_85_dot_local_is_local(tmp_path, stub_install, monkeypatch) -> None:
    result = _run_deploy_85(tmp_path, monkeypatch, {
        "domain": "foxhouse.local", "ssl_enabled": "0", "local_allow_block": "192.168.1.",
    })
    assert result["is_local"] is True
    assert result["deployment_mode"] == "http_local"
    assert result["local_allow_block"] == "192.168.1."
    config = result["_config"]
    assert "allow 192.168.1.0/24;" in config and "deny all;" in config
    assert "203.0.113.5" not in config


def test_deploy_85_local_only_override(tmp_path, stub_install, monkeypatch) -> None:
    result = _run_deploy_85(tmp_path, monkeypatch, {
        "domain": "intranet.example.com", "ssl_enabled": "0", "local_only": "1",
        "local_allow_block": "10.1.0.0/16",
    })
    assert result["is_local"] is True
    assert "allow 10.1.0.0/16;" in result["_config"]


def test_deploy_85_public_domain_stays_public(tmp_path, stub_install, monkeypatch) -> None:
    result = _run_deploy_85(tmp_path, monkeypatch, {
        "domain": "example.com", "ssl_enabled": "0", "local_allow_block": "192.168.1.0/24",
    })
    assert result["is_local"] is False
    assert result["deployment_mode"] == "http"
    assert "Client IP access control" not in result["_config"]
    assert "allow 192.168.1.0/24;" not in result["_config"]


def test_hooks_share_one_local_check() -> None:
    """deploy_85, deploy_86 and deploy_87 all decide locality through get_local_settings."""
    source = Path(nginx_hooks.__file__).read_text()
    assert source.count("get_local_settings(sec)") == 3
    assert "startswith('192.168.')" not in source
