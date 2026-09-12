"""Grafana webhook → Microsoft Graph sendMail bridge.

Listens on 127.0.0.1:8125 for Grafana alerting webhook POSTs and forwards
them as Graph sendMail calls using client-credentials OAuth2.

Reads credentials from environment (set via systemd EnvironmentFile=):
  GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, GRAPH_SENDER_EMAIL
  ALERT_RECIPIENT (defaults to GRAPH_SENDER_EMAIL)

Pattern lifted directly from bowling-league-tracker/check_health.py — same
Azure AD app/secret works for both.

Sentry eyecheck: when a firing alert carries the label `source: sentry`, the
bridge also runs the boiler-display reader's check script (a short RTSP
capture evaluated against the live calibration, no search) and sends a
second email with its report and the eyecheck image, so the display and the
quad can be judged from the phone. SENTRY_EYECHECK_CMD overrides the command
(empty disables it); SENTRY_EYECHECK_PNG is where the command writes the
image. At most one run per SENTRY_EYECHECK_MIN_INTERVAL_S (default 1800) so a
flapping rule cannot keep the camera busy. The fix stays manual: a search
cannot tell a stable misread from a right answer.
"""

import base64
import json
import logging
import os
import shlex
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN_HOST = '127.0.0.1'
LISTEN_PORT = 8125

SENTRY_EYECHECK_PNG = os.environ.get('SENTRY_EYECHECK_PNG', '/tmp/sentry-eyecheck.png')
SENTRY_EYECHECK_CMD = os.environ.get(
    'SENTRY_EYECHECK_CMD',
    '/home/pi/pivac-venv/bin/python /home/pi/github/pivac/scripts/sentry-warp-search.py '
    '--capture 300 --eyecheck ' + SENTRY_EYECHECK_PNG)
SENTRY_EYECHECK_MIN_INTERVAL_S = int(os.environ.get('SENTRY_EYECHECK_MIN_INTERVAL_S', '1800'))

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


def _send_email(subject, html_body, attachments=()):
    """attachments: (name, content_type, bytes) triples. Each is attached and
    also usable inline as <img src="cid:NAME">."""
    tenant_id     = os.environ['GRAPH_TENANT_ID']
    client_id     = os.environ['GRAPH_CLIENT_ID']
    client_secret = os.environ['GRAPH_CLIENT_SECRET']
    sender        = os.environ['GRAPH_SENDER_EMAIL']
    recipient     = os.environ.get('ALERT_RECIPIENT', sender)

    token = _graph_token(tenant_id, client_id, client_secret)
    message = {
        'subject': subject,
        'body':    {'contentType': 'HTML', 'content': html_body},
        'toRecipients': [{'emailAddress': {'address': recipient}}],
    }
    if attachments:
        message['attachments'] = [{
            '@odata.type': '#microsoft.graph.fileAttachment',
            'name':         name,
            'contentType':  content_type,
            'contentId':    name,
            'isInline':     True,
            'contentBytes': base64.b64encode(data).decode(),
        } for name, content_type, data in attachments]
    payload = json.dumps({'message': message, 'saveToSentItems': True}).encode()
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


def _sentry_alerts(payload):
    """Names of the firing alerts in this webhook that belong to the Sentry reader."""
    return [a.get('labels', {}).get('alertname', '?') for a in payload.get('alerts', [])
            if a.get('status') == 'firing' and a.get('labels', {}).get('source') == 'sentry']


_eyecheck_lock = threading.Lock()
_eyecheck_last = 0.0


def _run_sentry_eyecheck(alertnames):
    """Capture from the boiler camera, evaluate the live calibration, and email
    the report with the eyecheck image. Runs on its own thread after the alert
    email has gone out, so a slow capture never delays or fails the webhook."""
    global _eyecheck_last
    with _eyecheck_lock:
        if time.time() - _eyecheck_last < SENTRY_EYECHECK_MIN_INTERVAL_S:
            logger.info('sentry eyecheck skipped, last run %.0fs ago', time.time() - _eyecheck_last)
            return
        _eyecheck_last = time.time()
        try:
            os.unlink(SENTRY_EYECHECK_PNG)
        except FileNotFoundError:
            pass
        try:
            proc = subprocess.run(shlex.split(SENTRY_EYECHECK_CMD), capture_output=True,
                                  text=True, timeout=300)
            report = (proc.stdout + proc.stderr).strip()
            if proc.returncode != 0:
                report = f'exit {proc.returncode}\n{report}'
        except Exception as e:  # timeout, missing interpreter, ...
            report = f'eyecheck did not run: {e}'
        attachments = []
        try:
            with open(SENTRY_EYECHECK_PNG, 'rb') as fh:
                attachments.append(('eyecheck.png', 'image/png', fh.read()))
        except OSError:
            pass
        html = (
            f'<p>Triggered by: {", ".join(alertnames)}</p>'
            + (f'<p><img src="cid:eyecheck.png" alt="eyecheck"></p>' if attachments
               else '<p><em>no eyecheck image was written</em></p>')
            + f'<pre>{report[:6000]}</pre>'
            + '<p><small>Green boxes are the segment rectangles under the live quad; the '
              'line above each panel is what the reader decodes from that frame. '
              '"margin" is the lit/unlit separation in grey levels: 40 or more is sound, '
              'under 20 is a calibration on a knife edge.</small></p>'
        )
        try:
            _send_email('[Sentry eyecheck] ' + ', '.join(alertnames), html, attachments)
            logger.info('sent sentry eyecheck (%d bytes image)',
                        len(attachments[0][2]) if attachments else 0)
        except Exception:
            logger.exception('sentry eyecheck email failed')


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
            return

        sentry = _sentry_alerts(payload)
        if sentry and SENTRY_EYECHECK_CMD:
            threading.Thread(target=_run_sentry_eyecheck, args=(sentry,),
                             name='sentry-eyecheck', daemon=True).start()

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
