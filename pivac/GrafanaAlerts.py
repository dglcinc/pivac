"""pivac.GrafanaAlerts — Grafana's alert state as Signal K notifications.

Every alert rule Grafana evaluates is published every cycle under
`notifications.pivac.<rule uid>`, with state `normal` while the rule is quiet
and `warn`, `alert` or `alarm` (from the rule's `severity` label) while it
fires.  WilhelmSK shows Signal K notifications as alarms, so the phone sees
the same events the email path sends, without a second evaluator.

Grafana stays the evaluator.  The rules depend on 30-minute staleness
windows, `for:` durations, hours-long irrigation gating and cross-measurement
math, which Signal K's zone notifications do not do: those are threshold
checks on the live value, and staleness has no native alarm at all.
Re-implementing them in a plugin would duplicate Grafana and lose the
history queries.

Why poll rather than fan out from the webhook bridge: the bridge only hears
about transitions, so a Signal K restart would drop a firing alert until
Grafana's repeat notification, four hours by default.  Publishing the whole
set every cycle makes a restart of either side self-heal within one cycle,
and resolution is implicit when a rule leaves the firing set.  A dead poller
leaves every path stale together, which is the failure mode that is easy to
see.

Two Grafana endpoints.  The Prometheus-compatible rules API enumerates every
rule with its uid, title, labels and annotations, which is what makes the
`normal` set complete.  The Alertmanager alerts API says which of them are
firing and honours silences: a silenced rule is `suppressed` there and is
published as `normal`, matching what the email path does.  If that call
fails the rule's own `state` stands in, so a silence is the only thing lost
that cycle.

Reads only.  Needs a Grafana service-account token with the Viewer role; it
lives in /etc/pivac/config.yml on the Pi and never in the repo.
"""
import json
import logging
import re
import urllib.request

logger = logging.getLogger(__name__)

_DEFAULT_URL = "http://127.0.0.1:4000/grafana"
_RULES = "/api/prometheus/grafana/api/v1/rules"
_ALERTS = "/api/alertmanager/grafana/api/v2/alerts"

# Grafana's severity label -> Signal K notification state.  A rule without the
# label fires as warn, the level every pivac rule carries today.
STATE_BY_SEVERITY = {
    "critical": "alarm",
    "warning": "warn",
    "info": "alert",
}
METHOD_BY_STATE = {
    "emergency": ["visual", "sound"],
    "alarm": ["visual", "sound"],
    "warn": ["visual", "sound"],
    "alert": ["visual"],
    "normal": [],
}

# The set of firing paths last cycle, so a change logs once at WARNING.
_state = {"active": None}


def _get(url, token, timeout):
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer %s" % token,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.warning("GrafanaAlerts could not read %s (%s)", url, exc)
        return None


def path_segment(uid):
    """Rule uid -> one Signal K path segment, [a-z0-9_] only."""
    seg = re.sub(r"[^a-z0-9_]+", "_", str(uid).lower()).strip("_")
    return seg or "unnamed"


def rules_from(tree):
    """Flatten the rules API response to a list of rule dicts."""
    out = []
    try:
        groups = tree["data"]["groups"]
    except (KeyError, TypeError):
        return out
    for group in groups:
        for rule in group.get("rules") or []:
            if rule.get("type", "alerting") != "alerting":
                continue
            uid = rule.get("uid") or rule.get("name")
            if not uid:
                continue
            out.append({
                "uid": uid,
                "title": rule.get("name") or uid,
                "state": rule.get("state", "inactive"),
                "labels": rule.get("labels") or {},
                "annotations": rule.get("annotations") or {},
            })
    return out


def firing_from(alerts):
    """Alertmanager alerts -> {rule uid, and alertname: alert} for the ACTIVE
    ones.  Suppressed (silenced) alerts are left out on purpose.  None when
    the response is not a list, so the caller can fall back."""
    if not isinstance(alerts, list):
        return None
    firing = {}
    for alert in alerts:
        state = (alert.get("status") or {}).get("state", "active")
        if state != "active":
            continue
        labels = alert.get("labels") or {}
        for key in (labels.get("__alert_rule_uid__"), labels.get("alertname")):
            if key:
                firing[key] = alert
    return firing


def notification(rule, alert):
    """The Signal K notification value for one rule.  `alert` is the active
    Alertmanager alert, or None while the rule is quiet."""
    if alert is None:
        return {"state": "normal", "method": [], "message": rule["title"]}
    labels = alert.get("labels") or {}
    severity = labels.get("severity") or rule["labels"].get("severity") or ""
    state = STATE_BY_SEVERITY.get(str(severity).lower(), "warn")
    ann = alert.get("annotations") or rule["annotations"]
    summary = ann.get("summary") or ann.get("description") or ""
    message = "%s: %s" % (rule["title"], summary) if summary else rule["title"]
    return {"state": state, "method": list(METHOD_BY_STATE[state]), "message": message}


def build(rules, firing):
    """Everything status() publishes, keyed by path segment.  `firing` None
    means the Alertmanager call failed: each rule's own state stands in."""
    out = {}
    for rule in rules:
        if firing is None:
            alert = ({"labels": rule["labels"], "annotations": rule["annotations"]}
                     if rule["state"] == "firing" else None)
        else:
            alert = firing.get(rule["uid"]) or firing.get(rule["title"])
        out[path_segment(rule["uid"])] = notification(rule, alert)
    return out


def status(config={}, output="default"):
    base = config.get("grafana_url", _DEFAULT_URL).rstrip("/")
    token = config.get("token", "")
    timeout = float(config.get("request_timeout", 5))
    sk_path = config.get("sk_path", "notifications.pivac")

    rules = rules_from(_get(base + _RULES, token, timeout))
    if not rules:
        # A poller that cannot read Grafana publishes nothing, so every path
        # goes stale together rather than reading as quiet.
        return None
    firing = firing_from(_get(base + _ALERTS, token, timeout))
    if firing is None:
        logger.warning("GrafanaAlerts using rule state this cycle; silences not honoured")

    result = build(rules, firing)
    active = sorted(k for k, v in result.items() if v["state"] != "normal")
    if active != _state["active"]:
        logger.warning("GrafanaAlerts firing: %s", ", ".join(active) or "none")
        _state["active"] = active

    if output != "signalk":
        return result
    from pivac import sk_init_deltas, sk_add_source, sk_add_value
    deltas = sk_init_deltas()
    source = sk_add_source(deltas)
    for seg, value in sorted(result.items()):
        sk_add_value(source, "%s.%s" % (sk_path, seg), value)
    return deltas
