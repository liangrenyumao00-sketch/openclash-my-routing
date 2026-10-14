#!/usr/bin/env python3
"""Validate a public OpenClash overwrite module without using private subscriptions.

Online mode downloads official MRS files. --offline performs structural checks;
with --core it additionally requires already cached MRS files in --work-dir.
Mihomo remains the authority for YAML/core semantics; this script adds project
invariants such as local-first routing and publication-safe provider paths.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen

import yaml


BUILTINS = {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE"}
TEST_NODES = ["CI 香港 HK01", "CI 台湾 TW01", "CI 日本 JP01", "CI 新加坡 SG01", "CI 美国 US01", "CI 韩国 KR01"]
LOCAL_DOMAINS = {"lan", "local", "home.arpa"}
LOCAL_NETWORKS = {
    "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
    "100.64.0.0/10", "169.254.0.0/16", "::1/128", "fc00::/7", "fe80::/10",
}
PROVIDER_URL = re.compile(
    r"https://raw\.githubusercontent\.com/MetaCubeX/meta-rules-dat/meta/geo/"
    r"(geosite|geoip)/[a-zA-Z0-9_!@-]+\.mrs\Z"
)
MAX_MRS_BYTES = 32 * 1024 * 1024


class ValidationError(ValueError):
    """An error that must prevent publication."""


class UniqueKeyLoader(yaml.SafeLoader):
    """PyYAML otherwise silently discards the first duplicate mapping value."""


def _mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ValidationError(f"invalid or duplicate YAML key: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load_module(text: str) -> dict:
    """Read one INI [YAML] section and normalize supported overwrite keys."""
    sections = re.split(r"(?m)^\s*\[([A-Za-z]+)]\s*$", text.lstrip("\ufeff"))
    blocks = [sections[i + 1] for i in range(1, len(sections), 2) if sections[i] == "YAML"]
    if len(blocks) != 1:
        raise ValidationError("module must contain exactly one [YAML] section")
    try:
        raw = yaml.load(blocks[0], Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise ValidationError(f"invalid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValidationError("[YAML] must contain a mapping")
    normalized = {}
    for key, value in raw.items():
        canonical = key.removesuffix("!")
        if canonical in normalized:
            raise ValidationError(f"duplicate overwrite key: {canonical}")
        if canonical.startswith("+") or canonical.endswith(("+", "-", "*")) or canonical.startswith("<"):
            raise ValidationError(f"unsupported overwrite operator in fixture: {key}")
        normalized[canonical] = value
    # Real node data belongs on the router. CI never consumes a private provider.
    if "proxies" in normalized or "proxy-providers" in normalized:
        raise ValidationError("public module must not contain proxies or proxy-providers")
    return normalized


def _rule_parts(rule: str) -> tuple[str, str, str, list[str]]:
    if not isinstance(rule, str):
        raise ValidationError("every rule must be a string")
    parts = [part.strip() for part in rule.split(",")]
    flags = []
    while parts and parts[-1] in {"no-resolve", "src"}:
        flags.append(parts.pop())
    if len(parts) < 2:
        raise ValidationError(f"invalid rule: {rule}")
    kind, target = parts[0], parts[-1]
    payload = ",".join(parts[1:-1])
    if (kind == "MATCH" and len(parts) != 2) or (kind != "MATCH" and not payload):
        raise ValidationError(f"invalid rule: {rule}")
    return kind, payload, target, flags


def _provider_path(path: str) -> PurePosixPath:
    if not isinstance(path, str) or "\\" in path or ":" in path:
        raise ValidationError(f"unsafe provider path: {path!r}")
    result = PurePosixPath(path)
    if result.is_absolute() or ".." in result.parts or len(result.parts) < 2 or result.parts[0] != "rule_provider" or result.suffix != ".mrs":
        raise ValidationError(f"unsafe provider path: {path!r}; use rule_provider/*.mrs")
    return result


def validate_config(config: dict) -> None:
    groups = config.get("proxy-groups")
    providers = config.get("rule-providers", {})
    rules = config.get("rules")
    if not isinstance(groups, list) or not groups:
        raise ValidationError("proxy-groups must be a nonempty list")
    if not isinstance(providers, dict):
        raise ValidationError("rule-providers must be a mapping")
    if not isinstance(rules, list) or not rules:
        raise ValidationError("rules must be a nonempty list")
    names = set()
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("name"), str) or not group["name"]:
            raise ValidationError("every group needs a name")
        name = group["name"]
        if name in names or name in BUILTINS or name in TEST_NODES:
            raise ValidationError(f"duplicate/reserved group name: {name}")
        names.add(name)
    targets = names | BUILTINS | set(TEST_NODES)
    graph = {}
    for group in groups:
        name = group["name"]
        if group.get("type") not in {"select", "url-test", "fallback", "load-balance"}:
            raise ValidationError(f"unsupported group type: {name}")
        refs = group.get("proxies", [])
        if not isinstance(refs, list) or any(not isinstance(ref, str) or ref not in targets for ref in refs):
            raise ValidationError(f"unknown group/proxy reference in {name}: {refs!r}")
        if group.get("use"):
            raise ValidationError(f"private proxy provider reference is not allowed in public module: {name}")
        if not refs and not any(group.get(key) for key in ("include-all", "include-all-proxies", "include-all-providers")):
            raise ValidationError(f"group has no node source: {name}")
        fallback = group.get("empty-fallback", "COMPATIBLE")
        if fallback not in BUILTINS | set(TEST_NODES):
            raise ValidationError(f"empty-fallback must be a concrete proxy, not a group: {name}")
        graph[name] = [ref for ref in refs if ref in names]
    active, visited = set(), set()

    def visit(name):
        if name in active:
            raise ValidationError(f"group reference cycle at {name}")
        if name in visited:
            return
        active.add(name)
        for ref in graph[name]:
            visit(ref)
        active.remove(name)
        visited.add(name)

    for name in names:
        visit(name)
    paths = set()
    for name, provider in providers.items():
        if not isinstance(provider, dict):
            raise ValidationError(f"invalid provider: {name}")
        url = provider.get("url", "")
        match = PROVIDER_URL.fullmatch(url) if isinstance(url, str) else None
        if not match:
            raise ValidationError(f"provider URL must be an official HTTPS MetaCubeX MRS endpoint: {name}")
        expected_behavior = "domain" if match.group(1) == "geosite" else "ipcidr"
        if provider.get("type") != "http" or provider.get("format") != "mrs" or provider.get("behavior") != expected_behavior:
            raise ValidationError(f"provider type/format/behavior does not match URL: {name}")
        interval = provider.get("interval")
        if type(interval) is not int or interval <= 0:
            raise ValidationError(f"provider interval must be positive seconds: {name}")
        path = _provider_path(provider.get("path"))
        if path in paths:
            raise ValidationError(f"duplicate provider path: {path}")
        paths.add(path)
    parsed = [_rule_parts(rule) for rule in rules]
    matches = [i for i, item in enumerate(parsed) if item[0] == "MATCH"]
    if matches != [len(rules) - 1]:
        raise ValidationError("exactly one MATCH must be the last rule")
    domain_fallbacks = [i for i, item in enumerate(parsed) if item[:2] == ("DOMAIN-REGEX", ".+")]
    for index, (kind, payload, _target, flags) in enumerate(parsed):
        if kind == "RULE-SET" and payload in providers and providers[payload].get("behavior") == "ipcidr":
            if len(domain_fallbacks) != 1 or domain_fallbacks[0] >= index:
                raise ValidationError("unknown domain fallback must precede IP country fallback")
            if "no-resolve" not in flags:
                raise ValidationError("IP country fallback must use no-resolve")
    seen_local_domains, seen_local_networks = set(), set()
    left_local_prefix = False
    for index, (kind, payload, target, flags) in enumerate(parsed):
        if target not in targets:
            raise ValidationError(f"unknown rule target: {target}")
        if kind == "RULE-SET" and payload not in providers:
            raise ValidationError(f"unknown rule provider: {payload}")
        local_domain = kind == "DOMAIN-SUFFIX" and payload in LOCAL_DOMAINS
        local_ip = kind in {"IP-CIDR", "IP-CIDR6"} and payload in LOCAL_NETWORKS
        local_set = kind == "RULE-SET" and providers[payload]["url"].endswith("/private.mrs")
        if local_domain or local_ip or local_set:
            if left_local_prefix or target != "DIRECT":
                raise ValidationError(f"local/private rules must be first and DIRECT (rule {index + 1})")
            if local_ip and "no-resolve" not in flags:
                raise ValidationError(f"local IP rule must use no-resolve: {payload}")
            if local_domain:
                seen_local_domains.add(payload)
            if local_ip:
                seen_local_networks.add(payload)
        else:
            left_local_prefix = True
    if seen_local_domains != LOCAL_DOMAINS or seen_local_networks != LOCAL_NETWORKS:
        raise ValidationError("required local domains/private IP networks are missing")


def build_fixture(config: dict) -> dict:
    fixture = copy.deepcopy(config)
    fixture.update({"mode": "rule", "allow-lan": False, "proxies": [
        {"name": name, "type": "http", "server": "127.0.0.1", "port": 9}
        for name in TEST_NODES
    ]})
    return fixture


def write_fixture(config: dict, work_dir: Path) -> Path:
    work_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = work_dir / "fixture.yaml"
    fixture_path.write_text(yaml.safe_dump(build_fixture(config), allow_unicode=True, sort_keys=False), encoding="utf-8")
    return fixture_path


def check_mrs_data(data: bytes, name: str) -> None:
    # Official .mrs files use a Zstandard frame; the core checks decoded content.
    if len(data) < 8 or data[:4] != b"\x28\xb5\x2f\xfd":
        raise ValidationError(f"invalid/empty MRS download for {name}")


def fetch_providers(config: dict, work_dir: Path, offline=False) -> None:
    def fetch(item):
        name, provider = item
        target = work_dir.joinpath(*_provider_path(provider["path"]).parts)
        if offline:
            if not target.is_file():
                raise ValidationError(f"offline MRS cache is missing: {name}")
            check_mrs_data(target.read_bytes(), name)
            return
        request = Request(provider["url"], headers={"User-Agent": "openclash-routing-validation/1"})
        try:
            with urlopen(request, timeout=45) as response:
                if not PROVIDER_URL.fullmatch(response.url):
                    raise ValidationError(f"provider redirected outside allowed URL: {name}")
                data = response.read(MAX_MRS_BYTES + 1)
        except OSError as exc:
            raise ValidationError(f"cannot download provider {name}: {exc}") from exc
        if len(data) > MAX_MRS_BYTES:
            raise ValidationError(f"MRS download too large: {name}")
        check_mrs_data(data, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(fetch, config.get("rule-providers", {}).items()))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", nargs="?", type=Path, default=Path("My_Routing.ini"))
    parser.add_argument("--core", type=Path, help="Mihomo executable used for -t")
    parser.add_argument("--work-dir", type=Path, help="separate directory for synthetic config and provider cache")
    parser.add_argument("--offline", action="store_true", help="skip network; --core requires cached MRS files")
    args = parser.parse_args(argv)
    try:
        config = load_module(args.module.read_text(encoding="utf-8-sig"))
        validate_config(config)
        with tempfile.TemporaryDirectory(prefix="openclash-check-") as temporary:
            work_dir = (args.work_dir or Path(temporary)).resolve()
            fixture_path = write_fixture(config, work_dir)
            if not args.offline or args.core:
                fetch_providers(config, work_dir, offline=args.offline)
            if args.core:
                result = subprocess.run([str(args.core.resolve()), "-t", "-f", str(fixture_path), "-d", str(work_dir)], check=False)
                if result.returncode:
                    raise ValidationError(f"Mihomo configuration test failed (exit {result.returncode})")
        digest = hashlib.sha256(args.module.read_bytes()).hexdigest()
        print(f"Validated {len(config['proxy-groups'])} groups, {len(config.get('rule-providers', {}))} providers, {len(config['rules'])} rules")
        print(f"SHA256 {digest}  {args.module.name}")
        if not args.core:
            print("Mihomo core check not run (supply --core).")
        if args.offline and not args.core:
            print("Offline: provider downloads/content were not checked.")
        return 0
    except (OSError, ValidationError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
