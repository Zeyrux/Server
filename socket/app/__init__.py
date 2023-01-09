from socket import socket, AF_INET, SOCK_STREAM
from json import load
from pathlib import Path
from threading import Thread

from .models import Base, File, Event
from .models import Client as DBClient

from server_client_manager import recv_authentication, recv_file
from server_client_manager.data import Data
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


PATH_DATA = Path("data.json")


class Database:
    def __init__(self, db_path: Path | str) -> None:
        self.path = db_path if type(db_path).__name__ == "Path" else Path(db_path)
        self.engine = create_engine(f"sqlite:///{self.path}", echo=True)
        self.Base = Base
        self.Base.metadata.create_all(bind=self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.session.autocommit = True


class Client:
    def __init__(
        self,
        server: socket,
        db_server: Database,
        client: socket,
        addr: tuple[str, int],
        password_hash: str,
    ) -> None:
        self.server = server
        self.db_server = db_server
        self.client = client
        self.ip, self.port = addr
        self.password_hash = password_hash
        self.data = Data()
        self.db: Database = None

    def run(self):
        if self.authenticate():
            # recv database
            db_path = Path("app", "temp", secure_filename(f"{self.ip}.db"))
            recv_file(self.client, path=db_path)
            self.db = Database(db_path)
            self.sync()

    def sync(self):
        client_db = self.db_server.session.query(Client).filter(ip=self.ip).first()
        if client_db is None:
            self.db_server.session.add(DBClient(self.ip))

    def authenticate(self) -> None:
        req = self.client.recv(self.data.REQUEST_LENGHT).decode()
        self.client.send(self.data.SYNC)
        if req != self.data.SEND_AUTHENTICATION:
            return False
        if not check_password_hash(
            self.password_hash, recv_authentication(self.client)
        ):
            print(f"{self.client.getsockname()}: NOT Authenticated")
            return False
        return True


class Server:
    def __init__(self) -> None:
        data = load(open(PATH_DATA, "r"))
        self.host = data["host"]
        self.port = data["port"]
        self.password_hash = data["password_hash"]
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.data = Data()
        self.db = Database("db.db")

    def run(self) -> None:
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        while True:
            client, addr = self.socket.accept()
            thread = Thread(
                target=Client(
                    self.socket, self.db, client, addr, self.password_hash
                ).run,
                daemon=True,
            )
            thread.start()
