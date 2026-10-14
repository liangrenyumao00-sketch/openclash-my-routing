"""Regression tests for release-blocking routing mistakes; no network required."""

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate  # noqa: E402


MODULE = """[General]
#!NAME = Example
[YAML]
proxy-groups!:
  - {name: Proxy, type: select, proxies: [Auto, DIRECT]}
  - {name: Auto, type: url-test, include-all: true, empty-fallback: REJECT, url: 'https://www.gstatic.com/generate_204', interval: 300}
rule-providers:
  private: {type: http, behavior: domain, format: mrs, interval: 86400, path: ./rule_provider/private.mrs, url: 'https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/private.mrs'}
  china: {type: http, behavior: domain, format: mrs, interval: 86400, path: ./rule_provider/china.mrs, url: 'https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/cn.mrs'}
  china-ip: {type: http, behavior: ipcidr, format: mrs, interval: 86400, path: ./rule_provider/china-ip.mrs, url: 'https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geoip/cn.mrs'}
rules!:
  - RULE-SET,private,DIRECT
  - DOMAIN-SUFFIX,lan,DIRECT
  - DOMAIN-SUFFIX,local,DIRECT
  - DOMAIN-SUFFIX,home.arpa,DIRECT
  - IP-CIDR,127.0.0.0/8,DIRECT,no-resolve
  - IP-CIDR,10.0.0.0/8,DIRECT,no-resolve
  - IP-CIDR,172.16.0.0/12,DIRECT,no-resolve
  - IP-CIDR,192.168.0.0/16,DIRECT,no-resolve
  - IP-CIDR,100.64.0.0/10,DIRECT,no-resolve
  - IP-CIDR,169.254.0.0/16,DIRECT,no-resolve
  - IP-CIDR6,::1/128,DIRECT,no-resolve
  - IP-CIDR6,fc00::/7,DIRECT,no-resolve
  - IP-CIDR6,fe80::/10,DIRECT,no-resolve
  - RULE-SET,china,DIRECT
  - DOMAIN-REGEX,.+,Proxy
  - MATCH,Proxy
"""


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.config = validate.load_module(MODULE)

    def test_valid_module_builds_only_synthetic_loopback_nodes(self):
        validate.validate_config(self.config)
        fixture = validate.build_fixture(self.config)
        self.assertIn("rules", fixture)
        self.assertNotIn("rules!", fixture)
        self.assertEqual({p["server"] for p in fixture["proxies"]}, {"127.0.0.1"})
        self.assertEqual(len(fixture["proxies"]), 6)
        self.assertEqual(fixture["rules"][-1], "MATCH,Proxy")

    def test_dynamic_automatic_groups_reject_when_they_have_no_candidates(self):
        self.config["proxy-groups"][1].pop("empty-fallback")
        with self.assertRaisesRegex(validate.ValidationError, "empty-fallback"):
            validate.validate_config(self.config)

    def test_unknown_rule_target_blocks_release(self):
        self.config["rules"][-1] = "MATCH,Misspelled"
        with self.assertRaisesRegex(validate.ValidationError, "target"):
            validate.validate_config(self.config)

    def test_unknown_rule_provider_blocks_release(self):
        self.config["rules"].insert(-1, "RULE-SET,missing,Proxy")
        with self.assertRaisesRegex(validate.ValidationError, "provider"):
            validate.validate_config(self.config)

    def test_nested_group_cycle_blocks_release(self):
        self.config["proxy-groups"][1]["proxies"] = ["Proxy"]
        with self.assertRaisesRegex(validate.ValidationError, "cycle"):
            validate.validate_config(self.config)

    def test_unknown_group_reference_blocks_release(self):
        self.config["proxy-groups"][0]["proxies"].append("Missing")
        with self.assertRaisesRegex(validate.ValidationError, "reference"):
            validate.validate_config(self.config)

    def test_duplicate_group_names_block_release(self):
        self.config["proxy-groups"].append(copy.deepcopy(self.config["proxy-groups"][0]))
        with self.assertRaisesRegex(validate.ValidationError, "duplicate"):
            validate.validate_config(self.config)

    def test_only_official_https_mrs_urls_are_accepted(self):
        for url in ["http://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/cn.mrs",
                    "https://evil.example/cn.mrs",
                    "https://raw.githubusercontent.com/attacker/rules/main/cn.mrs",
                    "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/cn.mrs?token=secret"]:
            with self.subTest(url=url):
                config = copy.deepcopy(self.config)
                config["rule-providers"]["china"]["url"] = url
                with self.assertRaisesRegex(validate.ValidationError, "URL"):
                    validate.validate_config(config)

    def test_unsafe_or_shared_provider_paths_block_release(self):
        for path in ["../outside.mrs", "/tmp/outside.mrs", "rule_provider/../../outside.mrs", "./rule_provider/private.mrs"]:
            with self.subTest(path=path):
                config = copy.deepcopy(self.config)
                config["rule-providers"]["china"]["path"] = path
                with self.assertRaisesRegex(validate.ValidationError, "path"):
                    validate.validate_config(config)

    def test_local_rules_must_precede_service_rules(self):
        local_rule = self.config["rules"].pop(4)
        self.config["rules"].insert(-1, local_rule)
        with self.assertRaisesRegex(validate.ValidationError, "local"):
            validate.validate_config(self.config)

    def test_local_ip_rule_must_not_trigger_dns_resolution(self):
        self.config["rules"][4] = "IP-CIDR,127.0.0.0/8,DIRECT"
        with self.assertRaisesRegex(validate.ValidationError, "no-resolve"):
            validate.validate_config(self.config)

    def test_catchall_must_be_last(self):
        self.config["rules"].append("DOMAIN,example.com,DIRECT")
        with self.assertRaisesRegex(validate.ValidationError, "MATCH"):
            validate.validate_config(self.config)

    def test_unknown_domain_fallback_precedes_ip_country_fallback(self):
        self.config["rules"].insert(-2, "RULE-SET,china-ip,DIRECT,no-resolve")
        with self.assertRaisesRegex(validate.ValidationError, "domain fallback"):
            validate.validate_config(self.config)

    def test_repeated_yaml_keys_do_not_silently_override_rules(self):
        with self.assertRaisesRegex(validate.ValidationError, "duplicate"):
            validate.load_module(MODULE + "rules!: [MATCH,DIRECT]\n")

    def test_missing_yaml_section_is_rejected(self):
        with self.assertRaisesRegex(validate.ValidationError, "YAML"):
            validate.load_module("[General]\nRESTART = true\n")

    def test_fixture_write_uses_a_separate_work_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = validate.write_fixture(self.config, Path(directory))
            self.assertTrue(path.is_file())
            self.assertEqual(path.name, "fixture.yaml")
            self.assertIn("127.0.0.1", path.read_text(encoding="utf-8"))

    def test_html_or_empty_download_cannot_be_used_as_mrs(self):
        for data in [b"", b"<html>404</html>", b"\x28\xb5\x2f\xfd"]:
            with self.subTest(data=data):
                with self.assertRaisesRegex(validate.ValidationError, "MRS"):
                    validate.check_mrs_data(data, "test")


if __name__ == "__main__":
    unittest.main()
