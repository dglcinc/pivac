#!/usr/bin/env python3
"""pivac.GrafanaAlerts mapping: rules + Alertmanager alerts -> notifications.

Dependency-free: run directly with

    python tests/test_grafana_alerts.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pivac.GrafanaAlerts import (  # noqa: E402
    build, firing_from, notification, path_segment, rules_from,
)

RULES_API = {"status": "success", "data": {"groups": [
    {"name": "chiltrix", "rules": [
        {"type": "alerting", "uid": "chiltrix-pump-only-flow-low",
         "name": "Chiltrix startup flow low (water-side restriction)",
         "state": "firing", "labels": {"severity": "warning"},
         "annotations": {"summary": "startupFlow {{ $values.B }} L/min"}},
        {"type": "alerting", "uid": "chiltrix-modbus-stale",
         "name": "Chiltrix Modbus stale", "state": "inactive",
         "labels": {"severity": "warning"}, "annotations": {}},
    ]},
    {"name": "sentry", "rules": [
        {"type": "alerting", "uid": "sentry-outdoor-divergence",
         "name": "Sentry outdoor divergence", "state": "firing",
         "labels": {"severity": "info"}, "annotations": {"summary": "10 F apart"}},
        {"type": "recording", "uid": "ignored", "name": "a recording rule"},
    ]},
]}}

AM_API = [
    {"labels": {"alertname": "Chiltrix startup flow low (water-side restriction)",
                "__alert_rule_uid__": "chiltrix-pump-only-flow-low",
                "severity": "warning"},
     "annotations": {"summary": "startupFlow 36.8 L/min"},
     "status": {"state": "active", "silencedBy": []}},
    {"labels": {"alertname": "Sentry outdoor divergence",
                "__alert_rule_uid__": "sentry-outdoor-divergence",
                "severity": "info"},
     "annotations": {"summary": "10 F apart"},
     "status": {"state": "suppressed", "silencedBy": ["abc"]}},
]


def test_path_segment():
    assert path_segment("chiltrix-pump-only-flow-low") == "chiltrix_pump_only_flow_low"
    assert path_segment("Loop A (supply) stale!") == "loop_a_supply_stale"
    assert path_segment("---") == "unnamed"


def test_rules_flatten_and_skip_recording():
    rules = rules_from(RULES_API)
    assert [r["uid"] for r in rules] == [
        "chiltrix-pump-only-flow-low", "chiltrix-modbus-stale", "sentry-outdoor-divergence"]
    assert rules_from(None) == [] and rules_from({"data": {}}) == []


def test_alertmanager_honours_silences():
    firing = firing_from(AM_API)
    assert "chiltrix-pump-only-flow-low" in firing
    assert "sentry-outdoor-divergence" not in firing
    assert firing_from({"message": "unauthorized"}) is None


def test_build_with_alertmanager():
    out = build(rules_from(RULES_API), firing_from(AM_API))
    assert out["chiltrix_pump_only_flow_low"] == {
        "state": "warn", "method": ["visual", "sound"],
        "message": "Chiltrix startup flow low (water-side restriction): startupFlow 36.8 L/min"}
    assert out["chiltrix_modbus_stale"]["state"] == "normal"
    assert out["chiltrix_modbus_stale"]["method"] == []
    # silenced in Alertmanager -> normal, even though the rule itself is firing
    assert out["sentry_outdoor_divergence"]["state"] == "normal"


def test_build_falls_back_to_rule_state():
    out = build(rules_from(RULES_API), None)
    assert out["chiltrix_pump_only_flow_low"]["state"] == "warn"
    assert out["sentry_outdoor_divergence"]["state"] == "alert"     # info -> alert
    assert out["sentry_outdoor_divergence"]["method"] == ["visual"]
    assert out["chiltrix_modbus_stale"]["state"] == "normal"
    # rendered annotation is unavailable here, so the raw template stands
    assert "{{ $values.B }}" in out["chiltrix_pump_only_flow_low"]["message"]


def test_severity_mapping_defaults_to_warn():
    rule = {"uid": "x", "title": "X", "state": "firing", "labels": {}, "annotations": {}}
    assert notification(rule, {"labels": {}, "annotations": {}})["state"] == "warn"
    assert notification(rule, {"labels": {"severity": "critical"}})["state"] == "alarm"
    assert notification(rule, None) == {"state": "normal", "method": [], "message": "X"}


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except AssertionError as exc:
            failed += 1
            print("FAIL", name, "--", exc)
    print("%d/%d passed" % (len(tests) - failed, len(tests)))
    sys.exit(1 if failed else 0)
