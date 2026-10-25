"""Offline tests. Run: python -m unittest discover -s scripts -p test_server_upstream_timer.py"""
import gzip
import http.client
import io
import json
import os
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

import server_upstream_timer as timer


class Response:
    def __init__(self, status=200, data=None):
        self.status = status
        self.data = data
    def read(self, *args):
        return json.dumps(self.data).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


class Opener:
    def __init__(self, *results):
        self.results = list(results)
        self.requests = []
    def open(self, request, timeout):
        self.requests.append((request, timeout))
        result = self.results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


def http_error(code):
    return HTTPError('https://api.github.com/private', code, 'SECRET', {}, io.BytesIO(b'SECRET'))


def wire_response(body, headers=()):
    class Socket:
        def makefile(self, mode):
            return io.BytesIO(b'HTTP/1.1 200 OK\r\n' + b''.join(
                name.encode('ascii') + b': ' + value.encode('ascii') + b'\r\n'
                for name, value in headers) + b'\r\n' + body)
    response = http.client.HTTPResponse(Socket())
    response.begin()
    return response


class TimerTests(unittest.TestCase):
    def config(self, **kwargs):
        return timer.Config(**kwargs)
    def client(self, opener, **kwargs):
        return timer.GitHubClient(self.config(**kwargs), 'SECRET', opener=opener, wait=lambda seconds: False)
    def test_defaults(self):
        cfg = self.config()
        self.assertEqual((cfg.repo, cfg.workflow, cfg.ref, cfg.interval),
                         ('LeeXieXie/scoop-personal', 'upstream-watch.yml', 'master', 180))
    def test_get_negotiates_gzip_but_post_does_not(self):
        opener = Opener(Response(data={'workflow_runs': []}), Response(204))
        self.assertEqual(self.client(opener).cycle(), 'dispatched')
        self.assertEqual(opener.requests[0][0].get_header('Accept-encoding'), 'gzip')
        self.assertIsNone(opener.requests[1][0].get_header('Accept-encoding'))

    def test_real_identity_and_gzip_responses(self):
        body = b'{"workflow_runs": []}'
        for encoding in (None, 'identity', 'gzip', 'GZip'):
            with self.subTest(encoding=encoding):
                wire = gzip.compress(body) if encoding and encoding.lower() == 'gzip' else body
                headers = [('Content-Length', str(len(wire)))]
                if encoding:
                    headers.append(('Content-Encoding', encoding))
                opener = Opener(wire_response(wire, headers), Response(204))
                self.assertEqual(self.client(opener).cycle(), 'dispatched')

    def test_missing_and_invalid_content_length_fall_back_to_bounded_read(self):
        for value in (None, 'SECRET invalid', '-1', '1, 1'):
            with self.subTest(value=value):
                headers = [] if value is None else [('Content-Length', value)]
                opener = Opener(wire_response(b'{"workflow_runs": []}', headers), Response(204))
                self.assertEqual(self.client(opener).cycle(), 'dispatched')

    def test_valid_json_prefix_with_short_content_length_retries_before_dispatch(self):
        body = b'{"workflow_runs": []}'
        opener = Opener(wire_response(body, [('Content-Length', str(len(body) + 20))]),
                        Response(data={'workflow_runs': [{'status': 'queued'}]}))
        waits = []
        client = timer.GitHubClient(self.config(), 'SECRET', opener=opener,
                                   wait=lambda seconds: waits.append(seconds) or False)
        self.assertEqual(client.cycle(), 'busy')
        self.assertEqual(waits, [1])
        self.assertEqual([request.method for request, _ in opener.requests], ['GET', 'GET'])

    def test_short_content_length_exhaustion_is_sanitized_and_never_dispatches(self):
        body = b'{"workflow_runs": [], "SECRET": "remote body"}'
        headers = [('Content-Length', str(len(body) + 10)),
                   ('Content-Type', 'SECRET arbitrary-header')]
        opener = Opener(*(wire_response(body, headers) for _ in range(3)))
        output = io.StringIO()
        waits = []
        self.assertEqual(timer.main(['--once'], environ={'GH_TOKEN': 'SECRET'}, opener=opener,
                                    wait=lambda seconds: waits.append(seconds) or False,
                                    output=output), 1)
        message = json.loads(output.getvalue().splitlines()[-1])['message']
        self.assertIn('incomplete response body', message)
        self.assertIn(str(len(body)), message)
        self.assertNotIn('invalid JSON', message)
        for secret in ('SECRET', 'remote body', 'arbitrary-header'):
            self.assertNotIn(secret, output.getvalue())
        self.assertEqual(waits, [1, 2])
        self.assertEqual([request.method for request, _ in opener.requests], ['GET'] * 3)

    def test_chunked_transfer_overrides_content_length(self):
        body = b'{"workflow_runs": []}'
        chunked = f'{len(body):x}\r\n'.encode() + body + b'\r\n0\r\n\r\n'
        for length in ('1', str(8 * 1024 * 1024)):
            with self.subTest(length=length):
                opener = Opener(wire_response(chunked, [('Transfer-Encoding', 'chunked'),
                                                       ('Content-Length', length)]), Response(204))
                self.assertEqual(self.client(opener).cycle(), 'dispatched')

    def test_stdlib_noncanonical_content_length_retries_without_post(self):
        body = b'{"workflow_runs": []}'
        for length in ('+71', '7_1'):
            with self.subTest(length=length):
                response = wire_response(body, [('Content-Length', length)])
                opener = Opener(response, Response(data={'workflow_runs': [{'status': 'queued'}]}))
                waits = []
                client = timer.GitHubClient(self.config(), 'SECRET', opener=opener,
                                           wait=lambda seconds: waits.append(seconds) or False)
                self.assertEqual(client.cycle(), 'busy')
                self.assertEqual(waits, [1])
                self.assertEqual([request.method for request, _ in opener.requests], ['GET', 'GET'])

    def test_complete_stdlib_noncanonical_content_length_can_dispatch(self):
        body = b'{"workflow_runs": []}'
        for length in (f'+{len(body)}', f'{len(body) // 10}_{len(body) % 10}'):
            with self.subTest(length=length):
                opener = Opener(wire_response(body, [('Content-Length', length)]), Response(204))
                self.assertEqual(self.client(opener).cycle(), 'dispatched')
                self.assertEqual([request.method for request, _ in opener.requests], ['GET', 'POST'])

    def test_nonchunked_transfer_encoding_preserves_content_length_check(self):
        body = b'{"workflow_runs": []}'
        for encoding in ('identity', 'gzip', 'chunked, identity'):
            with self.subTest(encoding=encoding):
                response = wire_response(body, [('Content-Length', str(len(body) + 20)),
                                                ('Transfer-Encoding', encoding)])
                opener = Opener(response, Response(data={'workflow_runs': [{'status': 'queued'}]}))
                waits = []
                client = timer.GitHubClient(self.config(), 'SECRET', opener=opener,
                                           wait=lambda seconds: waits.append(seconds) or False)
                self.assertEqual(client.cycle(), 'busy')
                self.assertEqual(waits, [1])
                self.assertEqual([request.method for request, _ in opener.requests], ['GET', 'GET'])

    def test_incomplete_chunked_body_is_retryable(self):
        chunked = b'80\r\n{"SECRET": "remote body"}'
        opener = Opener(wire_response(chunked, [('Transfer-Encoding', 'chunked')]),
                        Response(data={'workflow_runs': [{'status': 'queued'}]}))
        self.assertEqual(self.client(opener).cycle(), 'busy')
        self.assertEqual([request.method for request, _ in opener.requests], ['GET', 'GET'])

    def test_incomplete_chunked_exhaustion_has_safe_body_diagnostic(self):
        opener = Opener(wire_response(b'80\r\nSECRET remote body',
                                     [('Transfer-Encoding', 'chunked')]))
        with self.assertRaises(timer.TimerError) as error:
            self.client(opener, get_retries=0).cycle()
        self.assertIn('incomplete response body', str(error.exception))
        self.assertNotIn('SECRET', str(error.exception))
        self.assertNotIn('remote body', str(error.exception))

    def test_corrupt_and_truncated_gzip_retry_then_fail_closed(self):
        compressed = gzip.compress(b'{"workflow_runs": [], "SECRET": "remote body"}')
        corrupt = compressed[:-8] + bytes([compressed[-8] ^ 1]) + compressed[-7:]
        for body in (b'', b'SECRET remote body', compressed[:-5], corrupt):
            with self.subTest(body=body):
                headers = [('Content-Encoding', 'gzip'), ('Content-Length', str(len(body)))]
                opener = Opener(*(wire_response(body, headers) for _ in range(3)))
                waits = []
                client = timer.GitHubClient(self.config(), 'SECRET', opener=opener,
                                           wait=lambda seconds: waits.append(seconds) or False)
                with self.assertRaises(timer.TimerError) as error:
                    client.cycle()
                message = str(error.exception)
                self.assertIn('invalid gzip response', message)
                self.assertNotIn('invalid JSON', message)
                self.assertNotIn('SECRET', message)
                self.assertNotIn('remote body', message)
                self.assertEqual(waits, [1, 2])
                self.assertEqual([request.method for request, _ in opener.requests], ['GET'] * 3)

    def test_gzip_failure_can_recover_without_retrying_post(self):
        headers = [('Content-Encoding', 'gzip')]
        opener = Opener(wire_response(b'not gzip', headers),
                        wire_response(gzip.compress(b'{"workflow_runs": []}'), headers),
                        TimeoutError('SECRET remote error'))
        with self.assertRaisesRegex(timer.TimerError, 'Not retried'):
            self.client(opener).cycle()
        self.assertEqual([request.method for request, _ in opener.requests], ['GET', 'GET', 'POST'])

    def test_unsupported_content_encoding_is_sanitized_and_never_dispatches(self):
        for encoding in ('br', 'gzip, identity', 'SECRET remote header'):
            with self.subTest(encoding=encoding):
                opener = Opener(wire_response(b'{"workflow_runs": []}',
                                             [('Content-Encoding', encoding)]))
                with self.assertRaisesRegex(timer.TimerError, 'unsupported content encoding') as error:
                    self.client(opener).cycle()
                self.assertNotIn(encoding, str(error.exception))
                self.assertEqual([request.method for request, _ in opener.requests], ['GET'])

    def test_wire_size_limit_with_and_without_gzip(self):
        for encoding in ('identity', 'gzip'):
            with self.subTest(encoding=encoding):
                body = b' ' * (4 * 1024 * 1024 + 1)
                opener = Opener(wire_response(body, [('Content-Encoding', encoding)]))
                with self.assertRaisesRegex(timer.TimerError, 'size limit'):
                    self.client(opener).cycle()
                self.assertEqual(len(opener.requests), 1)

    def test_identity_exact_size_boundary_and_large_numeric_length(self):
        limit = 4 * 1024 * 1024
        prefix = b'{"workflow_runs": []}'
        body = prefix + b' ' * (limit - len(prefix))
        opener = Opener(wire_response(body, [('Content-Length', str(limit))]), Response(204))
        self.assertEqual(self.client(opener).cycle(), 'dispatched')
        for length in (str(limit + 1), '9' * 5000):
            with self.subTest(length_bytes=len(length)):
                opener = Opener(wire_response(prefix, [('Content-Length', length)]))
                with self.assertRaisesRegex(timer.TimerError, 'size limit'):
                    self.client(opener).cycle()
                self.assertEqual(len(opener.requests), 1)

    def test_gzip_decoded_size_limit_and_exact_boundary(self):
        limit = 4 * 1024 * 1024
        for size in (limit, limit + 1, limit * 8):
            with self.subTest(size=size):
                prefix = b'{"workflow_runs": []}'
                compressed = gzip.compress(prefix + b' ' * (size - len(prefix)))
                opener = Opener(wire_response(compressed, [('Content-Encoding', 'gzip')]), Response(204))
                if size == limit:
                    self.assertEqual(self.client(opener).cycle(), 'dispatched')
                else:
                    with self.assertRaisesRegex(timer.TimerError, 'size limit'):
                        self.client(opener).cycle()
                    self.assertEqual(len(opener.requests), 1)

    def test_config_validation(self):
        for kwargs in ({'repo': '../bad'}, {'repo': 'a/b/c'}, {'repo': 'a/b?x'},
                       {'ref': '-bad'}, {'ref': 'a..b'}, {'ref': 'a\nb'}, {'ref': 'a.lock'},
                       {'ref': 'a@{b'}, {'ref': 'a//b'}, {'ref': 'a/'}, {'ref': 'a b'},
                       {'workflow': '../x'}, {'interval': 0}, {'interval': float('nan')},
                       {'timeout': -1}, {'get_retries': -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.config(**kwargs)
        self.config(ref='feature/a', repo='valid-owner/a.repo')
    def test_token_sources_and_safe_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'token')
            with open(path, 'w', encoding='utf-8') as out:
                out.write('SECRET\n')
            self.assertEqual(timer.load_token({'GH_TOKEN_FILE': path}), 'SECRET')
        self.assertEqual(timer.load_token({'GH_TOKEN': ' SECRET '}), 'SECRET')
        for env in ({}, {'GH_TOKEN': 'SECRET', 'GH_TOKEN_FILE': 'x'},
                    {'GH_TOKEN_FILE': 'SECRET/nonexistent'}, {'GH_TOKEN': 'a\nb'}):
            with self.subTest(env=env), self.assertRaises(ValueError) as error:
                timer.load_token(env)
            self.assertNotIn('SECRET', str(error.exception))
    def test_dispatch_and_accepted_post_codes(self):
        for status in (200, 201, 202, 204):
            opener = Opener(Response(data={'workflow_runs': []}), Response(status))
            self.assertEqual(self.client(opener).cycle(), 'dispatched')
            requests = [request for request, _ in opener.requests]
            self.assertEqual([r.method for r in requests], ['GET', 'POST'])
            self.assertIn('per_page=100', requests[0].full_url)
            self.assertEqual(json.loads(requests[1].data), {'ref': 'master'})
            self.assertTrue(all(r.full_url.startswith('https://api.github.com/') for r in requests))
    def test_queued_or_running_skips(self):
        for status in ('queued', 'in_progress', 'waiting', 'requested', 'pending', 'unknown'):
            opener = Opener(Response(data={'workflow_runs': [{'status': status}]}))
            self.assertEqual(self.client(opener).cycle(), 'busy')
            self.assertEqual(len(opener.requests), 1)
    def test_completed_allows_dispatch(self):
        opener = Opener(Response(data={'workflow_runs': [{'status': 'completed'}]}), Response(204))
        self.assertEqual(self.client(opener).cycle(), 'dispatched')
    def test_check_reads_permissions_and_queue_without_post(self):
        opener = Opener(Response(data={'permissions': {'push': True}}),
                        Response(data={'workflow_runs': []}))
        self.assertEqual(self.client(opener).cycle(check=True), 'checked')
        self.assertTrue(all(r.method == 'GET' for r, _ in opener.requests))
    def test_check_does_not_infer_actions_write_from_push(self):
        opener = Opener(Response(data={'permissions': {'push': False}}),
                        Response(data={'workflow_runs': []}))
        self.assertEqual(self.client(opener).cycle(check=True), 'checked')
    def test_get_retries_transient_errors(self):
        for failure in (TimeoutError('SECRET'), URLError('SECRET'), http_error(429), http_error(503)):
            opener = Opener(failure, Response(data={'workflow_runs': []}), Response(204))
            self.assertEqual(self.client(opener).cycle(), 'dispatched')
            self.assertEqual(len(opener.requests), 3)
    def test_get_retries_are_bounded(self):
        opener = Opener(http_error(429), http_error(429), http_error(429))
        with self.assertRaises(timer.TimerError):
            self.client(opener).cycle()
        self.assertEqual(len(opener.requests), 3)
    def test_permission_and_redirect_errors_never_retry_or_leak(self):
        for status in (301, 302, 307, 308, 401, 403):
            opener = Opener(http_error(status))
            with self.assertRaises(timer.TimerError) as error:
                self.client(opener).cycle()
            self.assertNotIn('SECRET', str(error.exception))
            self.assertEqual(len(opener.requests), 1)
    def test_redirect_handler_rejects(self):
        handler = timer.NoRedirect()
        self.assertIsNone(handler.redirect_request(Request('https://api.github.com'), None, 302,
                                                  'SECRET', {}, 'https://evil.example'))
    def test_post_uncertain_failure_not_retried_next_cycle_gets_first(self):
        for failure in (TimeoutError('SECRET'), http_error(503), http_error(429)):
            opener = Opener(Response(data={'workflow_runs': []}), failure,
                            Response(data={'workflow_runs': [{'status': 'queued'}]}))
            client = self.client(opener)
            with self.assertRaises(timer.TimerError) as error:
                client.cycle()
            self.assertNotIn('SECRET', str(error.exception))
            self.assertEqual(client.cycle(), 'busy')
            self.assertEqual([r.method for r, _ in opener.requests], ['GET', 'POST', 'GET'])
    def test_invalid_json_and_shape_fail_closed(self):
        for data in (None, {}, {'workflow_runs': 'bad'}, {'workflow_runs': [None]}):
            with self.subTest(data=data), self.assertRaises(timer.TimerError):
                self.client(Opener(Response(data=data))).cycle()
    def test_main_once_failure_and_check_no_post(self):
        output = io.StringIO()
        opener = Opener(http_error(403))
        self.assertEqual(timer.main(['--once'], environ={'GH_TOKEN': 'SECRET'},
                                    opener=opener, output=output), 1)
        self.assertNotIn('SECRET', output.getvalue())
        self.assertIn('403', output.getvalue())
        for line in output.getvalue().splitlines():
            json.loads(line)
        opener = Opener(Response(data={'permissions': {'push': True}}), Response(data={'workflow_runs': []}))
        self.assertEqual(timer.main(['--check'], environ={'GH_TOKEN': 'SECRET'},
                                    opener=opener, output=io.StringIO()), 0)
        self.assertEqual(len(opener.requests), 2)
    def test_loop_waits_after_error_and_stops(self):
        waits = []
        now = [0.0]
        def wait(seconds):
            waits.append(seconds)
            now[0] += seconds
            return len(waits) == 2
        opener = Opener(http_error(403), Response(data={'workflow_runs': []}), Response(204))
        self.assertEqual(timer.main([], environ={'GH_TOKEN': 'SECRET'}, opener=opener,
                                    wait=wait, monotonic=lambda: now[0], output=io.StringIO()), 0)
        self.assertEqual(waits, [180, 180])
    def test_keyboard_interrupt_and_pre_stopped(self):
        self.assertEqual(timer.main([], environ={'GH_TOKEN': 'SECRET'},
                                    opener=Opener(KeyboardInterrupt()), output=io.StringIO()), 0)
        event = threading.Event()
        event.set()
        opener = Opener()
        self.assertEqual(timer.main([], environ={'GH_TOKEN': 'SECRET'}, opener=opener,
                                    stop_event=event, output=io.StringIO()), 0)
        self.assertEqual(opener.requests, [])
    def test_sigterm_interrupts_wait_and_restores_handler(self):
        import signal
        previous = signal.getsignal(signal.SIGTERM)
        def wait(seconds):
            signal.raise_signal(signal.SIGTERM)
            return False
        opener = Opener(Response(data={'workflow_runs': []}), Response(204))
        self.assertEqual(timer.main([], environ={'GH_TOKEN': 'SECRET'}, opener=opener,
                                    wait=wait, output=io.StringIO()), 0)
        self.assertIs(signal.getsignal(signal.SIGTERM), previous)
    def test_timeout_and_headers_propagate(self):
        opener = Opener(Response(data={'workflow_runs': []}), Response(204))
        self.client(opener, timeout=7, ref='feature/a').cycle()
        self.assertEqual([timeout for _, timeout in opener.requests], [7, 7])
        self.assertEqual(opener.requests[0][0].get_header('Authorization'), 'Bearer SECRET')
        self.assertEqual(json.loads(opener.requests[1][0].data), {'ref': 'feature/a'})
    def test_get_requires_200_and_bad_json_is_sanitized(self):
        for status in (201, 202, 204):
            with self.assertRaises(timer.TimerError):
                self.client(Opener(Response(status))).cycle()
        response = Response()
        response.read = lambda *args: b'SECRET not json'
        with self.assertRaises(timer.TimerError) as error:
            self.client(Opener(response), get_retries=0).cycle()
        self.assertNotIn('SECRET', str(error.exception))
    def test_invalid_json_retries_then_dispatches(self):
        for body in (b'SECRET not json', b'\xffSECRET', b''):
            with self.subTest(body=body):
                response = Response()
                response.read = lambda *args: body
                opener = Opener(response, Response(data={'workflow_runs': []}), Response(204))
                waits = []
                client = timer.GitHubClient(self.config(), 'SECRET', opener=opener,
                                           wait=lambda seconds: waits.append(seconds) or False)
                self.assertEqual(client.cycle(), 'dispatched')
                self.assertEqual(waits, [1])
                self.assertEqual([r.method for r, _ in opener.requests], ['GET', 'GET', 'POST'])

    def test_invalid_json_exhaustion_is_safe_and_never_dispatches(self):
        body = b'SECRET remote body \xc3\xa9'
        for retries in (0, 2):
            with self.subTest(retries=retries):
                response = Response()
                response.read = lambda *args: body
                opener = Opener(*([response] * (retries + 1)))
                waits = []
                output = io.StringIO()
                result = timer.main(['--once', '--get-retries', str(retries)],
                                    environ={'GH_TOKEN': 'SECRET'}, opener=opener,
                                    wait=lambda seconds: waits.append(seconds) or False,
                                    output=output)
                self.assertEqual(result, 1)
                message = json.loads(output.getvalue().splitlines()[-1])['message']
                self.assertEqual(message, f'GET HTTP 200: invalid JSON (body bytes: {len(body)})')
                self.assertNotIn('SECRET', output.getvalue())
                self.assertNotIn('remote body', output.getvalue())
                self.assertEqual(waits, [1, 2][:retries])
                self.assertEqual([r.method for r, _ in opener.requests], ['GET'] * (retries + 1))

    def test_invalid_json_retry_wait_honors_stop(self):
        for set_event in (False, True):
            event = threading.Event()
            response = Response()
            response.read = lambda *args: b'SECRET invalid'
            opener = Opener(response)
            def wait(seconds):
                self.assertEqual(seconds, 1)
                if set_event:
                    event.set()
                return not set_event
            client = timer.GitHubClient(self.config(), 'SECRET', opener=opener,
                                       wait=wait, stop_event=event)
            with self.assertRaisesRegex(timer.TimerError, 'stopped during GET retry wait'):
                client.cycle()
            self.assertEqual(len(opener.requests), 1)

    def test_retry_wait_is_interruptible(self):
        opener = Opener(http_error(503))
        client = timer.GitHubClient(self.config(), 'SECRET', opener=opener, wait=lambda _: True)
        with self.assertRaises(timer.TimerError):
            client.cycle()
        self.assertEqual(len(opener.requests), 1)
    def test_retry_after_is_bounded(self):
        for value, expected in (('12', 12), ('99999', 30), ('bad', 1), ('-1', 1)):
            failure = http_error(429)
            failure.headers['Retry-After'] = value
            waits = []
            opener = Opener(failure, Response(data={'workflow_runs': []}), Response(204))
            client = timer.GitHubClient(self.config(), 'SECRET', opener=opener,
                                        wait=lambda seconds: waits.append(seconds) or False)
            client.cycle()
            self.assertEqual(waits, [expected])
    def test_check_busy_does_not_post(self):
        opener = Opener(Response(data={}), Response(data={'workflow_runs': [{'status': 'queued'}]}))
        self.assertEqual(self.client(opener).cycle(check=True), 'checked_busy')
        self.assertEqual([r.method for r, _ in opener.requests], ['GET', 'GET'])
    def test_fixed_start_cadence_and_missed_ticks(self):
        for interval in (180, 300):
            for duration in (0, 25, interval, interval + 25, interval * 3):
                with self.subTest(interval=interval, duration=duration):
                    now = [1000.0]
                    starts, waits = [], []
                    def cycle(client, check=False):
                        starts.append(now[0])
                        now[0] += duration
                        return 'dispatched'
                    def wait(seconds):
                        self.assertGreater(seconds, 0)
                        waits.append(seconds)
                        now[0] += seconds
                        return len(waits) == 3
                    output = io.StringIO()
                    with patch.object(timer.GitHubClient, 'cycle', cycle):
                        result = timer.main(['--interval', str(interval)],
                                            environ={'GH_TOKEN': 'SECRET'}, wait=wait,
                                            monotonic=lambda: now[0], output=output)
                    self.assertEqual(result, 0)
                    stride = (duration // interval + 1) * interval
                    self.assertEqual(starts, [1000, 1000 + stride, 1000 + 2 * stride])
                    self.assertEqual(waits, [stride - duration] * 3)
                    startup = json.loads(output.getvalue().splitlines()[0])
                    self.assertEqual(startup['interval_seconds'], interval)
                    self.assertEqual(startup['mode'], 'loop')
                    self.assertEqual(startup['schedule'], 'monotonic_fixed_start_skip_missed')
                    self.assertNotIn('SECRET', output.getvalue())

    def test_wall_clock_jumps_do_not_affect_failed_cycle_cadence(self):
        now = [0.0]
        waits = []
        def cycle(client, check=False):
            now[0] += 40
            raise timer.TimerError('safe failure')
        def wait(seconds):
            waits.append(seconds)
            now[0] += seconds
            return len(waits) == 2
        with patch.object(timer.GitHubClient, 'cycle', cycle), patch.object(timer, 'datetime') as wall:
            wall.now.side_effect = [unittest.mock.Mock(isoformat=lambda value=value: value)
                                    for value in ('2099', '1900', '2100', '1800')]
            self.assertEqual(timer.main([], environ={'GH_TOKEN': 'SECRET'}, wait=wait,
                                        monotonic=lambda: now[0], output=io.StringIO()), 0)
        self.assertEqual(waits, [140, 140])

    def test_stop_during_processing_never_waits_or_posts_again(self):
        event = threading.Event()
        def cycle(client, check=False):
            event.set()
            return 'stopped'
        with patch.object(timer.GitHubClient, 'cycle', cycle):
            self.assertEqual(timer.main([], environ={'GH_TOKEN': 'SECRET'}, stop_event=event,
                                        wait=lambda _: self.fail('wait after stop'),
                                        monotonic=lambda: 0, output=io.StringIO()), 0)

    def test_startup_modes_are_safe_and_check_remains_read_only(self):
        for mode in ('--once', '--check'):
            output = io.StringIO()
            opener = (Opener(Response(data={}), Response(data={'workflow_runs': []}))
                      if mode == '--check' else
                      Opener(Response(data={'workflow_runs': []}), Response(204)))
            self.assertEqual(timer.main([mode], environ={'GH_TOKEN': 'SECRET'}, opener=opener,
                                        wait=lambda _: self.fail('single mode waited'),
                                        output=output), 0)
            startup = json.loads(output.getvalue().splitlines()[0])
            self.assertEqual(startup['mode'], mode[2:])
            self.assertEqual(startup['interval_seconds'], 180)
            self.assertNotIn('SECRET', output.getvalue())
            if mode == '--check':
                self.assertTrue(all(r.method == 'GET' for r, _ in opener.requests))

    def test_config_exit_is_json(self):
        output = io.StringIO()
        self.assertEqual(timer.main(['--interval', '0'], environ={}, output=output), 2)
        self.assertEqual(json.loads(output.getvalue())['event'], 'configuration_error')


if __name__ == '__main__':
    unittest.main()
