"""library to handle cat control"""
import logging
import socket
import xmlrpc.client


class CAT:
    """CAT control rigctld or flrig"""

    def __init__(self, interface: str, host: str, port: int) -> None:
        """initializes cat"""
        self.server = None
        self.rigctrlsocket = None
        self.interface = interface.lower()
        self.host = host
        self.port = port
        if self.interface == "flrig":
            target = f"http://{host}:{port}"
            logging.info("cat_init: %s", target)
            self.server = xmlrpc.client.ServerProxy(target)
        if self.interface == "rigctld":
            self.__initialize_rigctrld()

    def __initialize_rigctrld(self):
        try:
            self.rigctrlsocket = socket.socket()
            self.rigctrlsocket.settimeout(0.5)
            self.rigctrlsocket.connect((self.host, self.port))
        except socket.error as exception:
            self.rigctrlsocket = None
            logging.warning("CAT __initialize_rigctrld: %s", exception)

    def get_vfo(self) -> str:
        """Poll the radio for current vfo using the interface"""
        vfo = ""
        if self.interface == "flrig":
            vfo = self.__getvfo_flrig()
            logging.warning("get_vfo: %s", vfo)
        if self.interface == "rigctld":
            vfo = self.__getvfo_rigctld()
            logging.warning("get_vfo: %s", vfo)
        return vfo

    def __getvfo_flrig(self) -> str:
        """Poll the radio using flrig"""
        try:
            return self.server.rig.get_vfo()
        except ConnectionRefusedError as exception:
            logging.warning("getvfo_flrig: %s", exception)
        except xmlrpc.client.Fault as exception:
            logging.warning(
                "getvfo_flrig: %d, %s", exception.faultCode, exception.faultString
            )
        return ""

    def __getvfo_rigctld(self) -> str:
        """Returns VFO freq returned from rigctld"""
        if self.rigctrlsocket is None:
            self.__initialize_rigctrld()
        if not self.rigctrlsocket is None:
            try:
                self.rigctrlsocket.settimeout(0.5)
                self.rigctrlsocket.send(b"f\n")
                return self.rigctrlsocket.recv(1024).decode().strip()
            except socket.error as exception:
                logging.warning("getvfo_rigctld: %s", exception)
                self.rigctrlsocket = None
            return ""

        self.__initialize_rigctrld()
        return ""

    def get_mode(self) -> str:
        """Returns the current mode filter width of the radio"""
        if self.interface == "flrig":
            return self.__getmode_flrig()
        if self.interface == "rigctld":
            return self.__getmode_rigctld()
        return ""

    def __getmode_flrig(self) -> str:
        """Returns mode via flrig"""
        try:
            return self.server.rig.get_mode()
        except ConnectionRefusedError as exception:
            logging.warning("getmode_flrig: %s", exception)
        return ""

    def __getmode_rigctld(self) -> str:
        """Returns mode vai rigctld"""
        if self.rigctrlsocket is None:
            self.__initialize_rigctrld()
        if not self.rigctrlsocket is None:
            try:
                self.rigctrlsocket.settimeout(0.5)
                self.rigctrlsocket.send(b"m\n")
                return self.rigctrlsocket.recv(1024).decode().strip().split()[0]
            except IndexError as exception:
                logging.warning("getmode_rigctld: %s", exception)
            except socket.error as exception:
                logging.warning("getmode_rigctld: %s", exception)
                self.rigctrlsocket = None
        return ""

    def set_vfo(self, freq: str) -> bool:
        """Sets the radios vfo"""
        if self.interface == "flrig":
            return self.__setvfo_flrig(freq)
        if self.interface == "rigctld":
            return self.__setvfo_rigctld(freq)
        return False

    def __setvfo_flrig(self, freq: str) -> bool:
        """Sets the radios vfo"""
        try:
            return self.server.rig.set_frequency(float(freq))
        except ConnectionRefusedError as exception:
            logging.warning("setvfo_flrig: %s", exception)
        return False

    def __setvfo_rigctld(self, freq: str) -> bool:
        """sets the radios vfo"""
        if self.rigctrlsocket is None:
            self.__initialize_rigctrld()
        if not self.rigctrlsocket is None:
            try:
                self.rigctrlsocket.settimeout(0.5)
                self.rigctrlsocket.send(bytes(f"F {freq}\n", "utf-8"))
                _ = self.rigctrlsocket.recv(1024).decode().strip()
                return True
            except socket.error as exception:
                logging.warning("setvfo_rigctld: %s", exception)
                self.rigctrlsocket = None
                return False
        return False

    def set_mode(self, mode: str) -> bool:
        """Sets the radios mode"""
        if self.interface == "flrig":
            return self.__setmode_flrig(mode)
        if self.interface == "rigctld":
            return self.__setmode_rigctld(mode)
        return False

    def __setmode_flrig(self, mode: str) -> bool:
        """Sets the radios mode"""
        try:
            return self.server.rig.set_mode(mode)
        except ConnectionRefusedError as exception:
            logging.warning("setmode_flrig: %s", exception)
        return False

    def __setmode_rigctld(self, mode: str) -> bool:
        """sets the radios mode"""
        if self.rigctrlsocket is None:
            self.__initialize_rigctrld()
        if not self.rigctrlsocket is None:
            try:
                self.rigctrlsocket.settimeout(0.5)
                self.rigctrlsocket.send(bytes(f"M {mode} 0\n", "utf-8"))
                _ = self.rigctrlsocket.recv(1024).decode().strip()
                return True
            except socket.error as exception:
                logging.warning("setmode_rigctld: %s", exception)
                self.rigctrlsocket = None
                return False
        return False
