#!/usr/bin/env python3
"""Server-side workflow_dispatch timer, Python 3.11+ standard library only.

Queue inspection covers the latest 100 runs, best-effort only, NOT a distributed
lock. Concurrent timers can race. --check performs read-only checks and cannot
prove Actions write permission. An uncertain POST is never automatically retried.
"""
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import http.client
import json
import math
import os
import re
import signal
import sys
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener


class TimerError(Exception):
    """A sanitized operational failure. Never contains remote response bodies."""


@dataclass(frozen=True)
class Config:
    repo: str = 'LeeXieXie/scoop-personal'
    workflow: str = 'upstream-watch.yml'
    ref: str = 'master'
    interval: float = 1800
    timeout: float = 30
    get_retries: int = 2

    def __post_init__(self):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9_.-]*', self.repo):
            raise ValueError('repo must be owner/name')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', self.workflow) or '..' in self.workflow:
            raise ValueError('workflow must be a workflow filename or numeric ID')
        if (not self.ref or self.ref == '@' or self.ref.startswith(('-', '/', '.'))
                or self.ref.endswith(('/', '.')) or '..' in self.ref or '@{' in self.ref
                or '//' in self.ref or re.search(r'[\x00-\x20\x7f~^:?*\[\\]', self.ref)
                or any(part.startswith('.') or part.endswith('.lock') for part in self.ref.split('/'))):
            raise ValueError('ref must be a valid branch or tag name')
        for value in (self.interval, self.timeout):
            if not math.isfinite(value) or value <= 0:
                raise ValueError('interval and timeout must be positive finite numbers')
        if not isinstance(self.get_retries, int) or not 0 <= self.get_retries <= 10:
            raise ValueError('get-retries must be an integer between 0 and 10')


def load_token(environ):
    """Use only explicitly configured token sources, never local gh credentials."""
    if 'GH_TOKEN' in environ and 'GH_TOKEN_FILE' in environ:
        raise ValueError('GH_TOKEN and GH_TOKEN_FILE are mutually exclusive')
    if 'GH_TOKEN_FILE' in environ:
        try:
            with open(environ['GH_TOKEN_FILE'], encoding='utf-8') as stream:
                token = stream.read(65537)
        except (OSError, ValueError, UnicodeError):
            raise ValueError('unable to read GH_TOKEN_FILE') from None
    else:
        token = environ.get('GH_TOKEN', '')
    token = token.strip()
    if not token or len(token) > 65536 or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise ValueError('a nonempty single-line GH_TOKEN or GH_TOKEN_FILE is required')
    return token


class NoRedirect(HTTPRedirectHandler):
    """Never forward bearer credentials to a redirect target."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHubClient:
    def __init__(self, config, token, *, opener=None, wait=None, stop_event=None):
        self.config = config
        self._token = token
        self.opener = opener if opener is not None else build_opener(NoRedirect())
        self.stop_event = stop_event if stop_event is not None else threading.Event()
        self.wait = wait if wait is not None else self.stop_event.wait
        self.repo_path = '/repos/' + config.repo
        self.workflow_path = self.repo_path + '/actions/workflows/' + quote(config.workflow, safe='')

    def request(self, method, path, payload=None):
        # Paths are constructed internally only. There is deliberately no base URL option.
        request = Request('https://api.github.com' + path, method=method,
                          headers={'Authorization': 'Bearer ' + self._token,
                                   'Accept': 'application/vnd.github+json',
                                   'X-GitHub-Api-Version': '2022-11-28',
                                   'User-Agent': 'scoop-personal-server-timer',
                                   'Content-Type': 'application/json'},
                          data=json.dumps(payload).encode('utf-8') if payload is not None else None)
        attempts = 1 + (self.config.get_retries if method == 'GET' else 0)
        for attempt in range(attempts):
            retryable = False
            retry_delay = min(2 ** attempt, 30)
            try:
                with self.opener.open(request, timeout=self.config.timeout) as response:
                    status = response.status
                    if method == 'GET' and status == 200:
                        body = response.read(4 * 1024 * 1024 + 1)
                        if len(body) > 4 * 1024 * 1024:
                            raise TimerError('GET response exceeds size limit')
                        try:
                            return json.loads(body)
                        except (ValueError, UnicodeError):
                            raise TimerError('GET returned invalid JSON') from None
                    if method == 'POST' and status in (200, 201, 202, 204):
                        return None
                    retryable = status == 429 or 500 <= status <= 599
                    message = self.http_message(method, status)
            except HTTPError as error:
                status = error.code
                retry_after = error.headers.get('Retry-After', '') if error.headers else ''
                # Bounded hint, not a promise to wait the full server-requested duration.
                if retry_after.isdigit():
                    retry_delay = max(retry_delay, min(int(retry_after[:10]), 30))
                error.close()
                retryable = status == 429 or 500 <= status <= 599
                message = self.http_message(method, status)
            except (URLError, OSError, http.client.HTTPException):
                retryable = True
                message = method + ' network/timeout failure'
            if method == 'POST':
                raise TimerError(message + '. Not retried: dispatch outcome may be uncertain') from None
            if not retryable or attempt + 1 == attempts:
                raise TimerError(message) from None
            if self.wait(retry_delay) or self.stop_event.is_set():
                raise TimerError('stopped during GET retry wait')
        raise TimerError('request failed')

    @staticmethod
    def http_message(method, status):
        if status in (401, 403):
            return f'{method} HTTP {status}: authentication/permission denied, check token Actions permissions and repository access'
        if 300 <= status < 400:
            return f'{method} HTTP {status}: redirect refused'
        return f'{method} HTTP {status}'

    def cycle(self, check=False):
        if check:
            repository = self.request('GET', self.repo_path)
            if not isinstance(repository, dict):
                raise TimerError('invalid repository metadata')
        data = self.request('GET', self.workflow_path + '/runs?per_page=100')
        if not isinstance(data, dict) or not isinstance(data.get('workflow_runs'), list):
            raise TimerError('invalid workflow runs response')
        runs = data['workflow_runs']
        if any(not isinstance(run, dict) or not isinstance(run.get('status'), str) for run in runs):
            raise TimerError('invalid workflow run status')
        busy = any(run['status'] != 'completed' for run in runs)
        if check:
            return 'checked_busy' if busy else 'checked'
        if busy:
            return 'busy'
        if self.stop_event.is_set():
            return 'stopped'
        self.request('POST', self.workflow_path + '/dispatches', {'ref': self.config.ref})
        return 'dispatched'


def main(argv=None, *, environ=None, opener=None, wait=None, stop_event=None, output=None):
    """Inject opener.open(Request, timeout), wait(seconds)->stopped for offline tests."""
    output = output if output is not None else sys.stdout
    def log(event, **fields):
        print(json.dumps({'time': datetime.now(timezone.utc).isoformat(), 'event': event, **fields}),
              file=output, flush=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='LeeXieXie/scoop-personal')
    parser.add_argument('--workflow', default='upstream-watch.yml')
    parser.add_argument('--ref', default='master')
    parser.add_argument('--interval', type=float, default=1800)
    parser.add_argument('--timeout', type=float, default=30)
    parser.add_argument('--get-retries', type=int, default=2)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--once', action='store_true')
    modes.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    try:
        config = Config(**{key: getattr(args, key) for key in Config.__dataclass_fields__})
        token = load_token(os.environ if environ is None else environ)
    except ValueError as error:
        log('configuration_error', message=str(error))
        return 2
    stop = stop_event if stop_event is not None else threading.Event()
    wait = wait if wait is not None else stop.wait
    previous = {}
    if threading.current_thread() is threading.main_thread():
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous[signum] = signal.signal(signum, lambda *_: stop.set())
    client = GitHubClient(config, token, opener=opener, wait=wait, stop_event=stop)
    try:
        while not stop.is_set():
            result = 0
            try:
                outcome = client.cycle(check=args.check)
                log(outcome, queue_check='best_effort_latest_100_not_a_distributed_lock',
                    **({'write_permission': 'not_verified_read_only_check'} if args.check else {}))
            except TimerError as error:
                log('cycle_failed', message=str(error))
                result = 1
            if args.once or args.check:
                return result
            # Fixed delay after completion, including failure. No catch-up bursts.
            if stop.is_set() or wait(config.interval):
                break
    except KeyboardInterrupt:
        stop.set()
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    log('stopped')
    return 0


if __name__ == '__main__':
    sys.exit(main())
