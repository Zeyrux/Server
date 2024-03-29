from socket import socket, AF_INET, SOCK_STREAM
from json import load
from pathlib import Path
from threading import Thread, get_ident
from datetime import datetime

from .models import (
    Base,
    File,
    Event,
    Change,
    EVENT_MODIFIED,
    EVENT_MOVED,
    EVENT_DELETED,
    EVENT_CREATED,
)
from .models import Client as DBClient

from server_client_manager import recv_authentication, recv_file
from server_client_manager.data import Data
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session


PATH_DATA = Path("server", "data.json")


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
        self.client_db_obj: DBClient = None

    def run(self) -> None:
        # if self.authenticate():
        # recv database
        db_path = Path("server", "app", "temp", secure_filename(f"{self.ip}.db"))
        # recv_file(self.client, path=db_path)
        self.db = Database(db_path)
        self.sync()

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

    def sync(self) -> None:
        self.client_db_obj = (
            self.db_server.session().query(DBClient).filter_by(ip=self.ip).first()
        )
        if self.client_db_obj is None:
            self.client_db_obj = DBClient(self.ip)
            self.db_server.session().add(self.client_db_obj)
            self.db_server.session().commit()
        print(self.client_db_obj.last_sync)
        print(self.db.session().query(Event).all())
        events: list[Event] = (
            self.db.session()
            .query(Event)
            .filter(Event.time > self.client_db_obj.last_sync)
            .order_by(Event.time)
            .all()
        )
        for event in events:
            self.handle_event(event)

    def handle_event(self, event: Event) -> None:
        # get src file
        src_file_server = (
            self.db_server.session()
            .query(File)
            .filter_by(path=event.ref_src_file.path)
            .first()
        )
        # get dest file
        dest_file_server = None
        if event.ref_dest_file is not None:
            dest_file_server = (
                self.db_server.session()
                .query(File)
                .filter_by(path=event.ref_dest_file.path)
                .first()
            )
        self.handle_file(event, src_file_server)
        self.handle_event(event, dest_file_server)

    def handle_file(self, event: Event, file_server: File) -> None:
        # check if there is another new version of file
        if file_server.changes[-1].time > event.time:
            # TODO: return error (2 file versions)
            return
        change = Change(file_server, self.client_db_obj, event.time)
        self.db_server.session().add(change)
        self.db_server.session().commit()


class Server:
    def __init__(self) -> None:
        data = load(open(PATH_DATA, "r"))
        self.host = data["host"]
        self.port = data["port"]
        self.password_hash = data["password_hash"]
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.data = Data()
        self.db = Database(Path("server", "db.db"))

    def run(self) -> None:
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        while True:
            # TODO: remove
            # client, addr = self.socket.accept()
            client, addr = (None, ("127.0.0.1", 53624))
            thread = Thread(
                target=Client(
                    self.socket, self.db, client, addr, self.password_hash
                ).run,
                daemon=True,
            )
            thread.start()
            # TODO: remove
            thread.join()
            break
