from json import load
from pathlib import Path
from socketserver import TCPServer, BaseRequestHandler
from multiprocessing import Process

from server_client_manager import recv_authentication
from server_client_manager.data import Data
from werkzeug.security import check_password_hash


PATH_DATA = Path("../data.json")


class RequestHandler(BaseRequestHandler):
    def __init__(self) -> None:
        self.password_hash = load(open(PATH_DATA, "r"))["password_hash"]
        self.data = Data()

    def authenticate(self, request) -> None:
        req = request.recv(self.data.REQUEST_LENGHT).encode()
        request.send(self.data.SYNC)
        if req != self.data.SEND_AUTHENTICATION:
            return
        if not check_password_hash(self.password_hash, recv_authentication(request)):
            return
    
    def setup(self) -> None:
        pass
    
    def handle(self) -> None:
        proc = Process(target=self.authenticate, daemon=True, args=[self.request])
    
    def finish(self) -> None:
        pass

def create_server() -> TCPServer:
    data = load(open(PATH_DATA, "r"))
    server = TCPServer((data["host"], data["port"]))
