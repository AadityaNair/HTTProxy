#!/usr/bin/env python3.4
'''
    HTTProxy
        - Aaditya M Nair
    A simple HTTP proxy with support for caching
'''

import multiprocessing as mp
import socket

PROXY_PORT = 1235
PROXY_HOST = '0.0.0.0'
BACKLOG = 10
DATA_SIZE = 1024
MAX_WORKERS = 5


class TCPClient(object):
    """
        This class is a simple abstraction of a client.
        You provide a url and it fetches you the appropriate response
        This is also supposed to interact with the cache.
        TODO Use as cache
    """

    def __init__(self):
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

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

def new_handle(t):
    buffer, conn, addr = t
    HTTPServer.handle(buffer, conn, addr)

class HTTPServer(object):
    """
        This is the proxy server class.
        Proxy is defined by two variables host and port.
        Both are changable above.
    """

    def __init__(self, host=PROXY_HOST, port=PROXY_PORT):
        self.hostname = host
        self.port = port

        self.pool = mp.Pool(processes = MAX_WORKERS)

    @staticmethod
    def handle(buffer, conn, addr):
        """
            The core logic of the proxy resides here.
            This function reads the data and forwards it to
            the appropriate host.
        """
        url = buffer.split('\r\n')[0].split(' ')[1]
        proto_end = url.find('//')
        res_start = url.find('/', proto_end+2)

        host = url[:res_start][proto_end+2:]
        resource = url[res_start:]
        print("LOG: ", host, " ", resource)  # TODO

        proxy_request = buffer.replace(url[:res_start], '')
        response_from_server = TCPClient().connect(host, 80, proxy_request)
        conn.send(response_from_server)
        conn.close()


    def serve(self):
        """
            Create a socket and bind to a given host/port pair.
            Wait for a connection and when you get one, send the entire
            data to the handler.
            TODO: Add multiprocessing
        """
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        soc.bind((self.hostname, self.port))
        soc.listen(BACKLOG)

        while True:
            conn, addr = soc.accept()
            conn.settimeout(0.1)
            buffer = ''

            while True:
                try:
                    data = conn.recv(DATA_SIZE)
                except socket.timeout:
                    break
                buffer += data.decode('ascii')

            self.pool.map(new_handle, [(buffer, conn, addr)])

if __name__ == '__main__':
    HTTPServer().serve()
