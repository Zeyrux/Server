from pathlib import Path
from datetime import datetime

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import Session, relationship
from sqlalchemy.dialects.sqlite import INTEGER, VARCHAR, DATETIME, BOOLEAN
from watchdog.events import (
    FileSystemEventHandler,
    FileModifiedEvent,
    FileMovedEvent,
    FileDeletedEvent,
    FileCreatedEvent,
)


EVENT_MODIFIED = 0
EVENT_MOVED = 1
EVENT_DELETED = 2
EVENT_CREATED = 3

Base = declarative_base()


class Client(Base):
    __tablename__ = "client"

    id = Column("id", INTEGER(), primary_key=True)
    ip = Column("ip", VARCHAR(15), unique=True, nullable=False)
    last_sync = Column("last_sync", DATETIME(), nullable=False)

    changes = relationship("Change", back_populates="client")

    def __init__(self, ip: str, last_sync: datetime) -> None:
        super().__init__()
        self.ip = ip
        self.last_sync = last_sync


class Change(Base):
    __tablename__ = "change"

    id = Column("id", INTEGER(), primary_key=True)
    id_file = Column("file", ForeignKey("file.id"), nullable=False)
    id_client = Column("client", ForeignKey("client.id"), nullable=False)
    time = Column("time", DATETIME, nullable=False)

    file = relationship("File", foreign_keys=id_file)
    client = relationship("Client", foreign_keys=id_client)

    def __init__(self, id_file: int, id_client: int, time: datetime) -> None:
        super().__init__()
        self.id_file = id_file
        self.id_client = id_client
        self.time = time

    def __repr__(self) -> str:
        return f"<{self.__tablename__}: {self.__dict__}>"


class File(Base):
    __tablename__ = "file"

    id = Column("id", INTEGER(), primary_key=True)
    path = Column("path", VARCHAR(512), nullable=False)
    size = Column("size", INTEGER(), nullable=False)
    change_date = Column("change_date", DATETIME(), nullable=False)
    exists = Column("exists", BOOLEAN(), nullable=False)

    changes = relationship("Change", back_populates="file")

    def __init__(
        self, path: str, size: int, change_date: datetime, exists: bool
    ) -> None:
        super().__init__()
        self.path = path
        self.size = size
        self.change_date = change_date
        self.exists = exists

    @staticmethod
    def from_file(file: "File") -> "File":
        return File(file.path, file.size, file.change_date, exists=file.exists)

    def __repr__(self) -> str:
        return f"<{self.__tablename__}: {self.__dict__}>"


class Event(Base):
    __tablename__ = "event"

    id = Column("id", INTEGER(), primary_key=True)
    event_type = Column("event_type", INTEGER(), nullable=False)
    id_src_file = Column("src_file", ForeignKey("file.id"), nullable=False)
    id_dest_file = Column("dest_file", ForeignKey("file.id"), nullable=True)
    time = Column("time", DATETIME(), nullable=False)

    src_file = relationship("File", foreign_keys=id_src_file)
    dest_file = relationship("File", foreign_keys=id_dest_file)

    def __init__(
        self, event_type: int, id_src_file: int, id_dest_file: int, time: datetime
    ) -> None:
        super().__init__()
        self.event_type = event_type
        self.id_src_file = id_src_file
        self.id_dest_file = id_dest_file
        self.time = time

    def __repr__(self) -> str:
        return f"<{self.__tablename__}: {self.__dict__}>"


def add_event(
    event: FileModifiedEvent | FileMovedEvent | FileDeletedEvent | FileCreatedEvent,
    session: Session,
) -> Event:
    # src file
    src_file = session.query(File).filter_by(path=event.src_path).first()
    if src_file is None:
        size = (
            Path(event.src_path).stat().st_size if Path(event.src_path).is_file() else 0
        )
        src_file = File(
            event.src_path, size, datetime.now(), True if size != 0 else False
        )
        session.add(src_file)
        session.commit()
    else:
        src_file.size = Path(src_file.path).stat().st_size
        src_file.change_date = datetime.now()
        # TODO: HERE
    # dest file
    dest_file = None
    if type(event) == FileMovedEvent:
        dest_file = session.query(File).filter_by(path=event.dest_path).first()
        if dest_file is None:
            size = (
                Path(event.dest_path).stat().st_size
                if Path(event.dest_path).is_file()
                else 0
            )
            dest_file = File(
                event.dest_path, size, datetime.now(), True if size != 0 else False
            )
            session.add(dest_file)
            session.commit()
    event = Event(
        {
            FileModifiedEvent: EVENT_MODIFIED,
            FileMovedEvent: EVENT_MOVED,
            FileDeletedEvent: EVENT_DELETED,
            FileCreatedEvent: EVENT_CREATED,
        }.get(type(event)),
        src_file.id,
        None if dest_file is None else dest_file.id,
        datetime.now(),
    )
    session.add(event)
    session.commit()
    return event
