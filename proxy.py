#!/usr/bin/env python3.4
"""
    HTTProxy
        - Aaditya M Nair
    A simple HTTP proxy with support for caching
"""

import socket
import multiprocessing as mp

PROXY_PORT = 1235
PROXY_HOST = '0.0.0.0'
BACKLOG = 10
DATA_SIZE = 1024
MAX_WORKERS = 5


class TCPClient(object):
    """
        This class is a simple abstraction of a client.
        You provide a url and it fetches you the appropriate response
    """

    def __init__(self):
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # @profile
    def connect(self, host, port=80, data="GET / HTTP/1.0\r\n\r\n"):
        self.soc.connect((host, port))
        self.soc.send(data.encode('ascii'))
        buffer = b''

        self.soc.settimeout(3)
        while True:
            try:
                data = self.soc.recv(DATA_SIZE)
            except socket.timeout:
                break
            buffer += data

        return buffer


class HTTPServer(object):
    """
        This is the proxy server class.
        Proxy is defined by two variables host and port.
        Both are changable above.
    """

    def __init__(self, port, host=PROXY_HOST):
        self.hostname = host
        self.port = port

        self.pool = mp.Pool(processes=MAX_WORKERS,
                            initializer=lambda: print('Started thread '+mp.current_process().name))
        self.cache = mp.Manager().dict()
        self.lock = mp.Manager().Lock()
        print("Cache and Lock Initialised\n")

    # @profile
    def serve(self):
        """
            Create a socket and bind to a given host/port pair.
            Wait for a connection and when you get one, send the entire
            data to the handler.
        """
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        soc.bind((self.hostname, self.port))
        soc.listen(BACKLOG)
        print("Binding to %s:%d\n" % (self.hostname, self.port))

        while True:
            conn, addr = soc.accept()
            conn.settimeout(0.1)
            buffer = ''

            while True:
                try:
                    data = conn.recv(DATA_SIZE)
                except socket.timeout:
                    break
                try:  # HACK to deal with HTTPS requests. Just close the connection !!!
                    buffer += data.decode('ascii')
                except UnicodeDecodeError:
                    conn.close()
                    print('Dropped an HTTPS request')
                    break

            # self.pool.map_async(handle, [(buffer, conn, addr)])
            self.pool.map_async(handle, [(buffer, conn, addr, self.cache, self.lock)])


# @profile
def handle(t):
    """
        The core logic of the proxy resides here.
        This function reads the data and forwards it to
        the appropriate host. This function also interacts with the cache.

        This is not in a class because multiprocessing does not want it to.
        Do not put this in a class as any form of *optimisation*
    """
    # buffer, conn, addr = t
    buffer, conn, addr, cache, lock = t

    url = buffer.split('\r\n')[0].split(' ')[1]
    proto_end = url.find('//')
    res_start = url.find('/', proto_end + 2)

    host = url[:res_start][proto_end + 2:]
    resource = url[res_start:]

    cached_response = cache.get(url, False)
    if cached_response:
        conn.send(cached_response)
        print(len(cached_response), " %s:%d "%(addr[0], addr[1]), ' ', host, ' ', resource, ' CacheHit')
    else:
        proxy_request = buffer.replace(url[:res_start], '')
        response_from_server = TCPClient().connect(host, 80, proxy_request)

        lock.acquire()
        cache[url] = response_from_server
        lock.release()

        conn.send(response_from_server)

        print(len(response_from_server), " %s:%d " % (addr[0], addr[1]), ' ', host, ' ', resource, ' CacheMiss')

    conn.close()


if __name__ == '__main__':
    import sys
    try:
        port = int(sys.argv[1])
    except (IndexError, ValueError):
        port = PROXY_PORT

    HTTPServer(port=port).serve()

