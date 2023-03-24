from socket import socket, AF_INET, SOCK_STREAM
from json import load
from pathlib import Path
from queue import Queue
from threading import get_ident

from .models import Base
from .collect import Collector

from server_client_manager import send_authentication, send_file
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


DATA_PATH = Path("client", "data.json")


class Database:
    def __init__(self, db_path: Path | str) -> None:
        self.path = db_path if type(db_path).__name__ == "Path" else Path(db_path)
        self.engine = create_engine(f"sqlite:///{self.path}")
        self.Base = Base
        self.Base.metadata.create_all(bind=self.engine)
        self.session_maker = sessionmaker(bind=self.engine)
        self.sessions = {}

    def session(self) -> Session:
        thread_id = get_ident()
        session = self.sessions.get(thread_id, None)
        if session is None:
            self.sessions[thread_id] = self.session_maker()
            session = self.sessions[thread_id]
        return session


class Client:
    def __init__(self) -> None:
        self.socket = socket(AF_INET, SOCK_STREAM)
        data = load(open(DATA_PATH, "r"))
        self.host = data["host"]
        self.port = data["port"]
        self.password = data["password"]
        self.queue = Queue()
        self.db = Database(Path("client", "db.db"))
        self.collector = Collector(self.db)

    def run(self) -> None:
        self.collector.run()
        while True:
            self.sync()
            self.queue.get()

    def sync(self) -> None:
        try:
            self.socket.connect((self.host, self.port))
        except ConnectionRefusedError:
            print("No connection possible ):")
            return
        send_authentication(self.socket, self.password)
        print("Authenticated")
        send_file(self.socket, self.db.path, send_path=False, send_request_type=False)
