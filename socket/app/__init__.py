from socket import socket, AF_INET, SOCK_STREAM
from json import load
from pathlib import Path
from threading import Thread, get_ident
from datetime import datetime

from .models import (
    Base,
    File,
    Event,
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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


PATH_DATA = Path("data.json")


class Database:
    def __init__(self, db_path: Path | str) -> None:
        self.path = db_path if type(db_path).__name__ == "Path" else Path(db_path)
        self.engine = create_engine(f"sqlite:///{self.path}", echo=True)
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

    def run(self) -> None:
        if self.authenticate():
            # recv database
            db_path = Path("app", "temp", secure_filename(f"{self.ip}.db"))
            recv_file(self.client, path=db_path)
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
        client_db = (
            self.db_server.session().query(DBClient).filter_by(ip=self.ip).first()
        )
        if client_db is None:
            client_db = DBClient(self.ip)
            self.db_server.session().add(client_db)
            self.db_server.session().commit()
        events: list[Event] = (
            self.db.session()
            .query(Event)
            .filter(Event.time > client_db.last_sync)
            .order_by(Event.time)
            .all()
        )
        for event in events:
            self.handle_event(event)

    def handle_event(self, event: Event) -> None:
        if not event.src_file.exists and event.event_type != EVENT_MOVED:
            self.mark_event_handelt(event)
        # get event path
        src_file_client = event.get_src_file(self.db.session())
        if src_file_client is None:
            self.mark_event_handelt(event)
        # get src_file from server
        src_file_server = (
            self.db_server.session()
            .query(File)
            .filter(File.path == src_file_client.path)
            .first()
        )
        if src_file_server is None:
            # TODO: event.src_file is number not the path
            src_file_server = File(
                event.src_file, datetime=datetime(2000, 1, 1, 0, 0, 0, 0)
            )
            self.db_server.session().add(src_file_server)
            self.db_server.session().commit()
        # get dest_file from server
        if event.event_type == EVENT_MODIFIED:
            self._handle_event_modified(event, src_file_server)
        elif event.event_type == EVENT_MOVED:
            self._handle_event_moved(event, src_file_server)
        elif event.event_type == EVENT_DELETED:
            pass
        elif event.event_type == EVENT_CREATED:
            pass

    def mark_event_handelt(self, event: Event) -> None:
        self.db_server.session().add(
            Event.from_other_db(self.db_server.session(), self.db, event)
        )
        self.db_server.session().commit()

    def _handle_event_modified(self, event: Event, src_file_server: File) -> None:
        if src_file_server.change_date < event.get_src_file().change_date:
            pass
            # TODO: some work
        # TODO: return error in syncing (2 versions of file)

    def _handle_event_moved(self, event: Event, src_file_server: File) -> None:
        if not event.dest_file.exists:
            src_file_server.exists = False
            self.db_server.session().commit()
        pass
        # TODO: some work


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
