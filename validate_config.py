#!/usr/bin/env python3
"""Validate rm-configs site configuration files.

Checks:
  - YAML parsing validity
  - mapping.yaml MD5 keys and structure
  - FE/main.yaml required fields, sitename consistency, switch/port definitions
  - Agent main.yaml required fields, interface/switch/port cross-references
  - VLAN range format and values
  - IP address/subnet pool validity
  - QoS configuration validity
  - Cross-site MD5 uniqueness and ASN collision detection
"""

import ipaddress
import re
import sys
from pathlib import Path

import yaml

# Directories at the repo root that are not site configs
SKIP_DIRS = {"CAs", "standarts", ".github", ".git"}

VALID_MAPPING_TYPES = {"FE", "Agent"}
VALID_PLUGINS = {"ansible", "raw"}
VALID_QOS_POLICIES = {"hostlevel", "privatens"}
VLAN_MIN = 1
VLAN_MAX = 4094
MD5_RE = re.compile(r"^[0-9a-f]{32}$")

# Known top-level keys in FE/main.yaml that are NOT site-specific sections
FE_RESERVED_KEYS = {"general"}
# Known top-level keys in agent main.yaml that are NOT interface sections
AGENT_RESERVED_KEYS = {"general", "agent", "qos"}


class ValidationReport:
    """Collects errors and warnings during validation."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, filepath, message):
        self.errors.append((str(filepath), message))

    def warning(self, filepath, message):
        self.warnings.append((str(filepath), message))

    def has_errors(self):
        return len(self.errors) > 0

    def print_report(self):
        for filepath, msg in self.warnings:
            print(f"WARNING [{filepath}]: {msg}")
        for filepath, msg in self.errors:
            print(f"ERROR   [{filepath}]: {msg}")
        print(f"\n{'='*60}")
        print(f"Errors: {len(self.errors)}  Warnings: {len(self.warnings)}")
        if not self.errors and not self.warnings:
            print("All configs valid.")


# ---------------------------------------------------------------------------
# Phase 0: Discovery
# ---------------------------------------------------------------------------

def discover_sites(base_dir):
    """Return {site_name: site_path} for directories containing mapping.yaml."""
    sites = {}
    for entry in sorted(base_dir.iterdir()):
        if not entry.is_dir() or entry.name in SKIP_DIRS or entry.name.startswith("."):
            continue
        if (entry / "mapping.yaml").exists():
            sites[entry.name] = entry
    return sites


# ---------------------------------------------------------------------------
# Phase 1: YAML parsing
# ---------------------------------------------------------------------------

def parse_yaml_files(sites, report):
    """Parse all .yaml files under site directories. Return {path: data}."""
    parsed = {}
    for site_name, site_path in sites.items():
        for yaml_file in sorted(site_path.rglob("*.yaml")):
            try:
                with open(yaml_file, "r", encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                parsed[yaml_file] = data
            except yaml.YAMLError as exc:
                mark = ""
                if hasattr(exc, "problem_mark") and exc.problem_mark:
                    pm = exc.problem_mark
                    mark = f" (line {pm.line + 1}, col {pm.column + 1})"
                report.error(yaml_file.relative_to(site_path.parent), f"YAML parse error{mark}: {exc.problem if hasattr(exc, 'problem') else exc}")
    return parsed


# ---------------------------------------------------------------------------
# VLAN range validation
# ---------------------------------------------------------------------------

def validate_vlan_range(vlan_range, filepath, context, report):
    """Validate a vlan_range value (list of ints/strings)."""
    if not isinstance(vlan_range, list):
        report.error(filepath, f"{context}: vlan_range must be a list, got {type(vlan_range).__name__}")
        return
    if not vlan_range:
        report.error(filepath, f"{context}: vlan_range is empty")
        return
    for item in vlan_range:
        if isinstance(item, int):
            if item < VLAN_MIN or item > VLAN_MAX:
                report.error(filepath, f"{context}: VLAN {item} outside valid range {VLAN_MIN}-{VLAN_MAX}")
        elif isinstance(item, str):
            parts = item.split("-")
            if len(parts) == 1:
                try:
                    v = int(parts[0])
                    if v < VLAN_MIN or v > VLAN_MAX:
                        report.error(filepath, f"{context}: VLAN {v} outside valid range {VLAN_MIN}-{VLAN_MAX}")
                except ValueError:
                    report.error(filepath, f"{context}: invalid VLAN value '{item}'")
            elif len(parts) == 2:
                try:
                    start, end = int(parts[0]), int(parts[1])
                except ValueError:
                    report.error(filepath, f"{context}: invalid VLAN range '{item}'")
                    continue
                if start >= end:
                    report.error(filepath, f"{context}: VLAN range '{item}' has start >= end")
                if start < VLAN_MIN or end > VLAN_MAX:
                    report.error(filepath, f"{context}: VLAN range '{item}' outside valid range {VLAN_MIN}-{VLAN_MAX}")
            else:
                report.error(filepath, f"{context}: invalid VLAN range format '{item}'")
        else:
            report.error(filepath, f"{context}: unexpected vlan_range item type {type(item).__name__}")


# ---------------------------------------------------------------------------
# IP pool validation
# ---------------------------------------------------------------------------

def validate_ip_pool(entries, expected_version, filepath, context, report):
    """Validate a list of IP address/subnet entries."""
    if not isinstance(entries, list):
        report.error(filepath, f"{context}: must be a list")
        return
    for entry in entries:
        entry_str = str(entry).strip()
        try:
            net = ipaddress.ip_network(entry_str, strict=False)
            if net.version != expected_version:
                report.error(filepath, f"{context}: '{entry_str}' is IPv{net.version}, expected IPv{expected_version}")
        except ValueError as exc:
            report.error(filepath, f"{context}: invalid IP network '{entry_str}': {exc}")


# ---------------------------------------------------------------------------
# Phase 2: Mapping validation
# ---------------------------------------------------------------------------

def validate_mapping(site_name, site_path, mapping_data, report, all_md5s):
    """Validate mapping.yaml structure and collect MD5s for cross-site check."""
    rel = Path(site_name) / "mapping.yaml"
    if not isinstance(mapping_data, dict):
        report.error(rel, "mapping.yaml must be a YAML dict")
        return

    for md5_key, entry in mapping_data.items():
        md5_str = str(md5_key)

        # Check hex format
        if not MD5_RE.match(md5_str):
            report.warning(rel, f"MD5 key '{md5_str}' is not a valid 32-char hex string")

        if not isinstance(entry, dict):
            report.error(rel, f"Entry for '{md5_str}' must be a dict")
            continue

        # Required fields
        if "type" not in entry:
            report.error(rel, f"Entry '{md5_str}' missing 'type' field")
        elif entry["type"] not in VALID_MAPPING_TYPES:
            report.error(rel, f"Entry '{md5_str}' has invalid type '{entry['type']}' (expected FE or Agent)")

        if "config" not in entry:
            report.error(rel, f"Entry '{md5_str}' missing 'config' field")
        else:
            config_dir = str(entry["config"]).rstrip("/")
            config_path = site_path / config_dir
            if not config_path.is_dir():
                report.error(rel, f"Entry '{md5_str}' config path '{config_dir}' does not exist")

        # Collect for cross-site check
        if md5_str in all_md5s:
            all_md5s[md5_str].append(site_name)
        else:
            all_md5s[md5_str] = [site_name]


# ---------------------------------------------------------------------------
# Phase 3: FE validation
# ---------------------------------------------------------------------------

def validate_fe_main(site_name, site_path, fe_data, report, all_asns):
    """Validate FE/main.yaml structure and values."""
    rel = Path(site_name) / "FE" / "main.yaml"

    if not isinstance(fe_data, dict):
        report.error(rel, "FE/main.yaml must be a YAML dict")
        return

    # --- general section ---
    general = fe_data.get("general")
    if not isinstance(general, dict):
        report.error(rel, "Missing or invalid 'general' section")
        return

    sitename = general.get("sitename")
    if not sitename:
        report.error(rel, "Missing 'general.sitename'")
        return

    if sitename != site_name:
        report.error(rel, f"general.sitename '{sitename}' does not match directory name '{site_name}'")

    if not general.get("webdomain"):
        report.error(rel, "Missing 'general.webdomain'")

    # --- site-specific section ---
    # The sitename should be a top-level key
    site_section = fe_data.get(sitename)
    if site_section is None:
        # Check if there's a different key that looks like a site section
        other_site_keys = [k for k in fe_data if k not in FE_RESERVED_KEYS and isinstance(fe_data[k], dict) and "domain" in fe_data[k]]
        if other_site_keys:
            report.error(rel, f"Site-specific section key '{other_site_keys[0]}' does not match general.sitename '{sitename}'")
        else:
            report.error(rel, f"Missing site-specific section '{sitename}'")
        return

    if not isinstance(site_section, dict):
        report.error(rel, f"Site-specific section '{sitename}' must be a dict")
        return

    # Also check for extra site-like sections that don't match sitename
    for key in fe_data:
        if key in FE_RESERVED_KEYS or key == sitename:
            continue
        val = fe_data[key]
        if isinstance(val, dict) and "domain" in val:
            report.error(rel, f"Extra site-specific section '{key}' found that does not match sitename '{sitename}'")

    # Required site section fields
    _check_required_field(site_section, "domain", str, rel, f"{sitename}.domain", report)
    _check_required_field(site_section, "latitude", (int, float), rel, f"{sitename}.latitude", report)
    _check_required_field(site_section, "longitude", (int, float), rel, f"{sitename}.longitude", report)
    _check_required_field(site_section, "year", int, rel, f"{sitename}.year", report)

    plugin = site_section.get("plugin")
    if not plugin:
        report.error(rel, f"Missing '{sitename}.plugin'")
    elif plugin not in VALID_PLUGINS:
        report.error(rel, f"'{sitename}.plugin' is '{plugin}', expected one of {VALID_PLUGINS}")

    switches = site_section.get("switch")
    if not switches or not isinstance(switches, list):
        report.error(rel, f"Missing or invalid '{sitename}.switch' (must be a non-empty list)")
        return

    # --- per-switch validation ---
    for switch_name in switches:
        switch_data = fe_data.get(switch_name)
        if switch_data is None:
            report.error(rel, f"Switch '{switch_name}' listed in '{sitename}.switch' but no top-level section found")
            continue
        if not isinstance(switch_data, dict):
            report.error(rel, f"Switch section '{switch_name}' must be a dict")
            continue

        # vlan_range
        vlan_range = switch_data.get("vlan_range")
        if vlan_range is None:
            report.error(rel, f"Switch '{switch_name}' missing 'vlan_range'")
        else:
            validate_vlan_range(vlan_range, rel, f"switch '{switch_name}'", report)

        # ports
        ports = switch_data.get("ports")
        if ports is None:
            report.error(rel, f"Switch '{switch_name}' missing 'ports'")
        elif not isinstance(ports, dict):
            report.error(rel, f"Switch '{switch_name}' 'ports' must be a dict")
        elif not ports:
            report.error(rel, f"Switch '{switch_name}' 'ports' is empty")
        else:
            # Validate per-port vlan_range if present
            for port_name, port_data in ports.items():
                if not isinstance(port_data, dict) or not port_data:
                    continue
                port_vlans = port_data.get("vlan_range")
                if port_vlans is not None:
                    validate_vlan_range(port_vlans, rel, f"switch '{switch_name}' port '{port_name}'", report)

        # private_asn
        asn = switch_data.get("private_asn")
        if asn is not None:
            if not isinstance(asn, int):
                report.error(rel, f"Switch '{switch_name}' private_asn must be an integer, got '{asn}'")
            else:
                key = str(asn)
                entry = (site_name, switch_name)
                if key in all_asns:
                    all_asns[key].append(entry)
                else:
                    all_asns[key] = [entry]

        # vrf
        vrf = switch_data.get("vrf")
        if vrf is not None and (not isinstance(vrf, str) or not vrf.strip()):
            report.error(rel, f"Switch '{switch_name}' vrf must be a non-empty string")

    # --- IP pool validation ---
    for pool_key, version in [("ipv6-subnet-pool", 6), ("ipv4-subnet-pool", 4),
                               ("ipv6-address-pool", 6), ("ipv4-address-pool", 4)]:
        pool = site_section.get(pool_key)
        if pool is not None:
            validate_ip_pool(pool, version, rel, f"{sitename}.{pool_key}", report)


def _check_required_field(data, key, expected_types, filepath, context, report):
    """Check a required field exists and has the expected type."""
    val = data.get(key)
    if val is None:
        report.error(filepath, f"Missing '{context}'")
    elif not isinstance(val, expected_types):
        report.error(filepath, f"'{context}' has wrong type: expected {expected_types}, got {type(val).__name__}")


# ---------------------------------------------------------------------------
# Phase 4: Agent validation
# ---------------------------------------------------------------------------

def is_kubernetes_agent(agent_data, interfaces):
    """Check if any interface uses kubeLabels pattern."""
    for intf_name in interfaces:
        intf_data = agent_data.get(intf_name)
        if isinstance(intf_data, dict) and "kubeLabels" in intf_data:
            return True
    return False


def validate_agent_main(site_name, site_path, agent_dir, agent_data, fe_data, report, is_disabled):
    """Validate an agent main.yaml."""
    rel = Path(site_name) / agent_dir / "main.yaml"

    if not isinstance(agent_data, dict):
        report.error(rel, "Agent main.yaml must be a YAML dict")
        return

    # --- general section ---
    general = agent_data.get("general")
    if not isinstance(general, dict):
        report.error(rel, "Missing or invalid 'general' section")
        return

    sitename = general.get("sitename")
    if not sitename:
        report.error(rel, "Missing 'general.sitename'")

    if not general.get("webdomain"):
        report.error(rel, "Missing 'general.webdomain'")

    # --- agent section ---
    agent_section = agent_data.get("agent")
    if not isinstance(agent_section, dict):
        report.error(rel, "Missing or invalid 'agent' section")
        return

    interfaces = agent_section.get("interfaces")
    if not interfaces or not isinstance(interfaces, list):
        report.error(rel, "Missing or invalid 'agent.interfaces' (must be a non-empty list)")
        return

    hostname = agent_section.get("hostname")
    if not hostname:
        report.error(rel, "Missing 'agent.hostname'")

    k8s_agent = is_kubernetes_agent(agent_data, interfaces)

    # Sitename consistency (skip for k8s agents that reference different sites)
    if sitename and not k8s_agent and sitename != site_name:
        report.error(rel, f"general.sitename '{sitename}' does not match directory name '{site_name}'")

    # Webdomain consistency with FE
    if fe_data and not k8s_agent:
        fe_general = fe_data.get("general", {})
        fe_webdomain = fe_general.get("webdomain", "")
        agent_webdomain = general.get("webdomain", "")
        if fe_webdomain and agent_webdomain and fe_webdomain != agent_webdomain:
            report.warning(rel, f"general.webdomain '{agent_webdomain}' does not match FE webdomain '{fe_webdomain}'")

    # Build switch/port lookup from FE for cross-reference checks
    # fe_switches: {switch_name: {"ports": set(...), "allports": bool}}
    fe_switches = {}
    if fe_data and not is_disabled and not k8s_agent:
        fe_sitename = fe_data.get("general", {}).get("sitename", "")
        fe_site_section = fe_data.get(fe_sitename, {})
        switch_list = fe_site_section.get("switch", []) if isinstance(fe_site_section, dict) else []
        for sw_name in switch_list:
            sw_data = fe_data.get(sw_name, {})
            if isinstance(sw_data, dict):
                ports = sw_data.get("ports", {})
                allports = sw_data.get("allports", False)
                fe_switches[sw_name] = {
                    "ports": set(ports.keys()) if isinstance(ports, dict) else set(),
                    "allports": bool(allports),
                }

    # --- per-interface validation ---
    for intf_name in interfaces:
        intf_data = agent_data.get(intf_name)
        if intf_data is None:
            report.error(rel, f"Interface '{intf_name}' listed in agent.interfaces but no top-level section found")
            continue
        if not isinstance(intf_data, dict):
            report.error(rel, f"Interface section '{intf_name}' must be a dict")
            continue

        # vlan_range
        vlan_range = intf_data.get("vlan_range")
        if vlan_range is not None:
            validate_vlan_range(vlan_range, rel, f"interface '{intf_name}'", report)
        elif "kubeLabels" not in intf_data:
            report.error(rel, f"Interface '{intf_name}' missing 'vlan_range'")

        # Connection type: port+switch, kubeLabels, or isAlias
        has_port_switch = "port" in intf_data and "switch" in intf_data
        has_kube = "kubeLabels" in intf_data
        has_alias = "isAlias" in intf_data

        if not has_port_switch and not has_kube and not has_alias:
            report.error(rel, f"Interface '{intf_name}' must have 'port'+'switch', 'kubeLabels', or 'isAlias'")
            continue

        # Cross-reference check for port+switch
        if has_port_switch and fe_switches and not is_disabled:
            switch_ref = intf_data["switch"]
            port_ref = intf_data["port"]
            if switch_ref not in fe_switches:
                report.error(rel, f"Interface '{intf_name}' references switch '{switch_ref}' not found in FE config")
            elif not fe_switches[switch_ref]["allports"] and port_ref not in fe_switches[switch_ref]["ports"]:
                report.error(rel, f"Interface '{intf_name}' references port '{port_ref}' not found in FE switch '{switch_ref}'")

    # --- QoS validation ---
    qos = agent_data.get("qos")
    if isinstance(qos, dict):
        policy = qos.get("policy")
        if policy is not None and policy not in VALID_QOS_POLICIES:
            report.error(rel, f"qos.policy '{policy}' is invalid, expected one of {VALID_QOS_POLICIES}")

        qos_intfs = qos.get("interfaces")
        if isinstance(qos_intfs, dict) and qos_intfs:
            for qos_intf_name, qos_intf_data in qos_intfs.items():
                if not isinstance(qos_intf_data, dict):
                    continue
                master = qos_intf_data.get("master_intf")
                if not master:
                    report.warning(rel, f"QoS interface '{qos_intf_name}' missing 'master_intf'")
                elif master not in interfaces:
                    report.warning(rel, f"QoS interface '{qos_intf_name}' master_intf '{master}' not in agent.interfaces")


# ---------------------------------------------------------------------------
# Phase 5: Cross-site checks
# ---------------------------------------------------------------------------

def validate_md5_uniqueness(all_md5s, report):
    """Check that no MD5 hash is used in multiple sites."""
    for md5_hash, site_list in all_md5s.items():
        if len(site_list) > 1:
            sites_str = ", ".join(site_list)
            report.error("cross-site", f"MD5 '{md5_hash}' appears in multiple sites: {sites_str}")


def validate_asn_uniqueness(all_asns, report):
    """Warn if the same ASN is used across different sites."""
    for asn, entries in all_asns.items():
        sites = set(site for site, _ in entries)
        if len(sites) > 1:
            detail = ", ".join(f"{site}/{switch}" for site, switch in entries)
            report.warning("cross-site", f"ASN {asn} used by multiple sites: {detail}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    base_dir = Path(__file__).parent
    report = ValidationReport()

    # Phase 0: Discovery
    sites = discover_sites(base_dir)
    if not sites:
        print("No site directories found.")
        sys.exit(1)
    disabled_sites = {name for name, path in sites.items() if (path / "disabled").exists()}
    print(f"Found {len(sites)} sites ({len(disabled_sites)} disabled)")

    # Phase 1: YAML parsing
    parsed_files = parse_yaml_files(sites, report)
    print(f"Parsed {len(parsed_files)} YAML files")

    # Phase 2: Mapping validation
    all_md5s = {}
    for site_name, site_path in sites.items():
        mapping_file = site_path / "mapping.yaml"
        if mapping_file in parsed_files and parsed_files[mapping_file]:
            validate_mapping(site_name, site_path, parsed_files[mapping_file], report, all_md5s)

    # Phase 3: FE validation
    all_asns = {}
    fe_data_by_site = {}
    for site_name, site_path in sites.items():
        fe_file = site_path / "FE" / "main.yaml"
        if fe_file in parsed_files and parsed_files[fe_file]:
            fe_data = parsed_files[fe_file]
            fe_data_by_site[site_name] = fe_data
            validate_fe_main(site_name, site_path, fe_data, report, all_asns)

    # Phase 4: Agent validation
    for site_name, site_path in sites.items():
        mapping_file = site_path / "mapping.yaml"
        if mapping_file not in parsed_files or not parsed_files[mapping_file]:
            continue
        mapping_data = parsed_files[mapping_file]
        if not isinstance(mapping_data, dict):
            continue
        for md5_key, entry in mapping_data.items():
            if not isinstance(entry, dict) or entry.get("type") != "Agent":
                continue
            config_dir = str(entry.get("config", "")).rstrip("/")
            if not config_dir:
                continue
            # Check both main.yaml and _main.yaml (disabled agents)
            agent_file = site_path / config_dir / "main.yaml"
            if agent_file not in parsed_files:
                continue
            agent_data = parsed_files[agent_file]
            if not agent_data:
                continue
            is_disabled = (
                site_name in disabled_sites
                or (site_path / config_dir / "disabled").exists()
            )
            fe_data = fe_data_by_site.get(site_name)
            validate_agent_main(site_name, site_path, config_dir, agent_data, fe_data, report, is_disabled)

    # Phase 5: Cross-site checks
    validate_md5_uniqueness(all_md5s, report)
    validate_asn_uniqueness(all_asns, report)

    # Report
    print()
    report.print_report()
    sys.exit(1 if report.has_errors() else 0)


if __name__ == "__main__":
    main()
