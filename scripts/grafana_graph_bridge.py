"""Grafana webhook → Microsoft Graph sendMail bridge.

Listens on 127.0.0.1:8125 for Grafana alerting webhook POSTs and forwards
them as Graph sendMail calls using client-credentials OAuth2.

Reads credentials from environment (set via systemd EnvironmentFile=):
  GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, GRAPH_SENDER_EMAIL
  ALERT_RECIPIENT (defaults to GRAPH_SENDER_EMAIL)

Pattern lifted directly from bowling-league-tracker/check_health.py — same
Azure AD app/secret works for both.
"""

import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN_HOST = '127.0.0.1'
LISTEN_PORT = 8125

logger = logging.getLogger('grafana-graph-bridge')


def _graph_token(tenant_id, client_id, client_secret):
    data = urllib.parse.urlencode({
        'grant_type':    'client_credentials',
        'client_id':     client_id,
        'client_secret': client_secret,
        'scope':         'https://graph.microsoft.com/.default',
    }).encode()
    req = urllib.request.Request(
        f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token',
        data=data, method='POST',
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())['access_token']


def _send_email(subject, html_body):
    tenant_id     = os.environ['GRAPH_TENANT_ID']
    client_id     = os.environ['GRAPH_CLIENT_ID']
    client_secret = os.environ['GRAPH_CLIENT_SECRET']
    sender        = os.environ['GRAPH_SENDER_EMAIL']
    recipient     = os.environ.get('ALERT_RECIPIENT', sender)

    token = _graph_token(tenant_id, client_id, client_secret)
    payload = json.dumps({
        'message': {
            'subject': subject,
            'body':    {'contentType': 'HTML', 'content': html_body},
            'toRecipients': [{'emailAddress': {'address': recipient}}],
        },
        'saveToSentItems': True,
    }).encode()
    req = urllib.request.Request(
        f'https://graph.microsoft.com/v1.0/users/{sender}/sendMail',
        data=payload,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type':  'application/json',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=15):
        pass  # 202 Accepted


def _format_alert(payload):
    """Render Grafana's webhook JSON into a subject + HTML body."""
    status = payload.get('status', 'unknown')
    title  = payload.get('title') or payload.get('message') or 'Grafana alert'
    alerts = payload.get('alerts', [])

    subject = f'[Grafana {status.upper()}] {title}'

    rows = []
    for a in alerts:
        labels = a.get('labels', {})
        annot  = a.get('annotations', {})
        rows.append(
            f'<li><strong>{a.get("status", "")}</strong> — '
            f'<code>{labels.get("alertname", "?")}</code><br>'
            f'{annot.get("summary", "")}<br>'
            f'<small>{annot.get("runbook", "")}</small></li>'
        )

    html = (
        f'<p><strong>Status:</strong> {status}</p>'
        f'<p><strong>Title:</strong> {title}</p>'
        f'<ul>{"".join(rows)}</ul>'
        f'<hr><pre>{json.dumps(payload, indent=2)[:4000]}</pre>'
    )
    return subject, html


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/alert':
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get('Content-Length', '0'))
        try:
            payload = json.loads(self.rfile.read(length) or b'{}')
        except json.JSONDecodeError as e:
            logger.warning('bad JSON: %s', e)
            self.send_response(400)
            self.end_headers()
            return

        subject, html = _format_alert(payload)
        try:
            _send_email(subject, html)
            logger.info('sent: %s', subject)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')
        except Exception as e:
            logger.exception('graph send failed')
            self.send_response(502)
            self.end_headers()
            self.wfile.write(f'graph error: {e}'.encode())

    def log_message(self, fmt, *args):
        logger.info('%s - %s', self.client_address[0], fmt % args)


def main():
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        level=logging.INFO,
        stream=sys.stderr,
    )
    for k in ('GRAPH_TENANT_ID', 'GRAPH_CLIENT_ID', 'GRAPH_CLIENT_SECRET', 'GRAPH_SENDER_EMAIL'):
        if not os.environ.get(k):
            logger.error('missing required env var: %s', k)
            sys.exit(1)

    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    logger.info('listening on http://%s:%d/alert', LISTEN_HOST, LISTEN_PORT)
    server.serve_forever()


if __name__ == '__main__':
    main()
