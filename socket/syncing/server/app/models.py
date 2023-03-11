from pathlib import Path
from datetime import datetime

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.sqlite import INTEGER, VARCHAR, DATETIME, BOOLEAN


EVENT_MODIFIED = 0
EVENT_MOVED = 1
EVENT_DELETED = 2
EVENT_CREATED = 3

Base = declarative_base()


class Client(Base):
    __tablename__ = "clients"

    id = Column("id", INTEGER(), primary_key=True)
    ip = Column("ip", VARCHAR(15), unique=True, nullable=False)
    last_sync = Column("last_sync", DATETIME(), nullable=False)

    def __init__(self, ip, last_sync: datetime = None) -> None:
        self.ip = ip
        self.last_sync = (
            last_sync if last_sync is not None else datetime(2000, 1, 1, 0, 0, 0, 0)
        )


class File(Base):
    __tablename__ = "files"

    id = Column("id", INTEGER(), primary_key=True)
    path = Column("path", VARCHAR(512), nullable=False)
    size = Column("size", INTEGER(), nullable=False)
    change_date = Column("change_date", DATETIME(), nullable=False)
    exists = Column("exists", BOOLEAN(), nullable=False)

    def __init__(
        self,
        path: Path | str,
        size: int = None,
        change_date: datetime = datetime.now(),
        exists: bool = True,
    ) -> None:
        self.path = path
        self.size = (
            size
            if size is not None
            else Path(self.path).stat().st_size
            if Path(self.path).exists()
            else 0
        )
        self.change_date = change_date
        self.exists = exists

    @staticmethod
    def from_file(file: "File", change_date=None):
        if change_date is None:
            change_date = file.change_date
        return File(file.path, file.size, change_date, exists=file.exists)

    def __repr__(self) -> str:
        return f"<{self.__tablename__}: {self.__dict__}>"


class Event(Base):
    __tablename__ = "events"

    id = Column("id", INTEGER(), primary_key=True)
    client = Column("client", ForeignKey("clients.id"), nullable=False)
    event_type = Column("event_type", INTEGER(), nullable=False)
    src_file = Column("src_file", ForeignKey("files.id"), nullable=False)
    dest_file = Column("dest_file", ForeignKey("files.id"), nullable=True)
    time = Column("time", DATETIME(), nullable=False)

    src_file_obj = None
    dest_file_obj = None

    def __init__(
        self,
        session: Session,
        event_type: str | int,
        src_path: Path | str | int,
        dest_path: Path | str | int = None,
        time: datetime = datetime.now(),
    ) -> None:
        self.time = time
        if type(event_type).__name__ == "str":
            event_type = (
                EVENT_MODIFIED
                if event_type == "modified"
                else EVENT_MOVED
                if event_type == "moved"
                else EVENT_DELETED
                if event_type == "deleted"
                else EVENT_CREATED
                if event_type == "created"
                else None
            )
        self.event_type = event_type
        # add src_file if not exists
        if type(src_path) == int:
            self.src_file = session.query(File).filter_by(id=src_path).first()
        else:
            self.src_file = session.query(File).filter_by(path=str(src_path)).first()
        if self.src_file is None:
            self.src_file = File(src_path)
            session.add(self.src_file)
        # add dest_file if not exists
        if dest_path is not None:
            if type(dest_path) == int:
                self.dest_file = session.query(File).filter_by(id=dest_path).first()
            else:
                self.dest_file = (
                    session.query(File).filter_by(path=str(dest_path)).first()
                )
            if self.dest_file is None:
                self.dest_file = File(dest_path)
                session.add(self.dest_file)
        # handle remove
        if event_type == EVENT_DELETED:
            self.src_file.exists = False
        # handle create
        if event_type == EVENT_CREATED:
            self.src_file.exists = True
        # turn files into path
        self.src_file = self.src_file.id
        if self.dest_file is not None:
            self.dest_file = self.dest_file.id

    @staticmethod
    def from_other_db(
        session_new_event: Session, session_existing_event: Session, event: "Event"
    ) -> "Event":
        return Event(
            session_new_event,
            event.event_type,
            event.src_path(session_existing_event),
            dest_path=event.dest_path(session_existing_event)
            if event.dest_file is not None
            else None,
            time=event.time,
        )

    def src_path(self, session: Session) -> Path:
        return Path(self.get_src_file(session).path)

    def dest_path(self, session: Session) -> Path:
        return Path(self.get_dest_file(session).path)

    def get_src_file(self, session: Session) -> File:
        if self.src_file_obj is None:
            self.src_file_obj = (
                session.query(File).filter(File.id == self.src_file).first()
            )
        return self.src_file_obj

    def get_dest_file(self, session: Session) -> File:
        if self.dest_file_obj is None:
            self.dest_file_obj = (
                session.query(File).filter(File.id == self.dest_file).first()
            )
        return self.dest_file_obj

    def __repr__(self) -> str:
        return f"<{self.__tablename__}: {self.__dict__}>"
