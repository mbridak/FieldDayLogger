"""Impliments CW abstraction layer"""
from xmlrpc.client import ServerProxy, Error
import socket
import logging
from pathlib import Path


class CW:
    """An interface to cwdaemon and PyWinkeyerSerial"""

    def __init__(self, servertype: int, host: str, port: int) -> None:
        self.logger = logging.getLogger("__name__")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            datefmt="%H:%M:%S",
            fmt="[%(asctime)s] %(levelname)s %(module)s - %(funcName)s Line %(lineno)d:\n%(message)s",
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        if Path("./debug").exists():
            # if True:
            self.logger.setLevel(logging.DEBUG)
            print("debugging on")
        else:
            self.logger.setLevel(self.logger.warning)
        self.servertype = servertype
        self.host = host
        self.port = port

    def sendcw(self, texttosend):
        """sends cw to k1el"""
        self.logger.info("sendcw: %s", texttosend)
        if self.servertype == 2:
            self._sendcw_xmlrpc(texttosend)
        if self.servertype == 1:
            self._sendcw_udp(texttosend)

    def _sendcw_xmlrpc(self, texttosend):
        """sends cw to xmlrpc"""
        self.logger.info("xmlrpc: %s", texttosend)
        with ServerProxy(f"http://{self.host}:{self.port}") as proxy:
            try:
                proxy.k1elsendstring(texttosend)
            except Error as exception:
                self.logger.info(
                    "http://%s:%s, xmlrpc error: %s", self.host, self.port, exception
                )
            except ConnectionRefusedError:
                self.logger.info(
                    "http://%s:%s, xmlrpc Connection Refused", self.host, self.port
                )

    def _sendcw_udp(self, texttosend):
        """send cw to udp port"""
        self.logger.info("UDP: %s", texttosend)
        server_address_port = (self.host, self.port)
        # bufferSize          = 1024
        udp_client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        udp_client_socket.sendto(bytes(texttosend, "utf-8"), server_address_port)
