from socket import socket, AF_INET, SOCK_STREAM
from json import load
from pathlib import Path
from threading import Thread

from server_client_manager import recv_authentication
from server_client_manager.data import Data
from werkzeug.security import check_password_hash, generate_password_hash


PATH_DATA = Path("data.json")


class Client:
    def __init__(self, server: socket, client: socket, password_hash: str) -> None:
        self.server = server
        self.client = client
        self.password_hash = password_hash
        self.data = Data()

    def run(self):
        self.authenticate()

    def authenticate(self) -> None:
        req = self.client.recv(self.data.REQUEST_LENGHT).decode()
        self.client.send(self.data.SYNC)
        if req != self.data.SEND_AUTHENTICATION:
            return
        if not check_password_hash(
            self.password_hash, recv_authentication(self.client)
        ):
            print(f"{self.client.getsockname()}: NOT Authenticated")
            return
        print(f"{self.client.getsockname()}: Authenticated")


class Server:
    def __init__(self) -> None:
        data = load(open(PATH_DATA, "r"))
        self.host = data["host"]
        self.port = data["port"]
        self.password_hash = data["password_hash"]
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.data = Data()

    def run(self) -> None:
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        while True:
            client, addr = self.socket.accept()
            thread = Thread(
                target=Client(self.socket, client, self.password_hash).run,
                daemon=True,
            )
            thread.start()


def create_server() -> Server:
    server = Server()
    return server
