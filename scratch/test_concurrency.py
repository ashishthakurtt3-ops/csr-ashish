import os
import sys
import time
import threading
import urllib.request
import django

sys.path.insert(0, os.path.abspath('.'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.core.servers.basehttp import WSGIServer, ThreadedWSGIServer, WSGIRequestHandler

class SlowWSGIApp:
    def __init__(self):
        self.events = []

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        t_start = time.perf_counter()
        if 'sleep' in path:
            time.sleep(1.0)
            status = '200 OK'
            headers = [('Content-Type', 'text/plain')]
            start_response(status, headers)
            return [b"slept 1.0s"]
        else:
            status = '200 OK'
            headers = [('Content-Type', 'text/plain')]
            start_response(status, headers)
            return [b"fast"]

# Start ThreadedWSGIServer on an ephemeral port
server = ThreadedWSGIServer(('127.0.0.1', 8999), WSGIRequestHandler)
server.set_app(SlowWSGIApp())
srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
srv_thread.start()

time.sleep(0.1)

results = {}

def req_sleep():
    t0 = time.perf_counter()
    resp = urllib.request.urlopen('http://127.0.0.1:8999/sleep').read()
    results['sleep'] = time.perf_counter() - t0

def req_fast():
    time.sleep(0.2)  # Fire while sleep is running
    t0 = time.perf_counter()
    resp = urllib.request.urlopen('http://127.0.0.1:8999/fast').read()
    results['fast'] = time.perf_counter() - t0

t_sleep = threading.Thread(target=req_sleep)
t_fast = threading.Thread(target=req_fast)

t_start = time.perf_counter()
t_sleep.start()
t_fast.start()

t_sleep.join()
t_fast.join()
total_time = time.perf_counter() - t_start

server.shutdown()
server.server_close()

print(f"Sleep request took: {results['sleep']:.3f}s")
print(f"Fast request took: {results['fast']:.3f}s")
print(f"Total concurrent time: {total_time:.3f}s")
if results['fast'] < 0.5:
    print("FINDING: runserver (ThreadedWSGIServer) is MULTI-THREADED and DOES NOT BLOCK concurrent requests!")
else:
    print("FINDING: runserver BLOCKS concurrent requests.")
