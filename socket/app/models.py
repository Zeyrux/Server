from pathlib import Path
from datetime import datetime

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.sqlite import INTEGER, VARCHAR, DATETIME, BOOLEAN


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

    def __repr__(self) -> str:
        return f"<{self.__tablename__}: {self.__dict__}>"


class Event(Base):
    __tablename__ = "events"

    # event types:
    # 0 file modified
    # 1 file moved
    # 2 file deleted
    # 3 file created
    id = Column("id", INTEGER(), primary_key=True)
    client = Column("client", ForeignKey("clients.id"), nullable=False)
    event_type = Column("event_type", INTEGER(), nullable=False)
    src_file = Column("src_file", ForeignKey("files.id"), nullable=False)
    dest_file = Column("dest_file", ForeignKey("files.id"), nullable=True)
    time = Column("time", DATETIME(), nullable=False)

    def __init__(
        self,
        session: Session,
        event_type: str | int,
        src_path: str,
        dest_path: str = None,
        time: datetime = datetime.now(),
    ) -> None:
        self.time = time
        if type(event_type).__name__ == "str":
            event_type = (
                0
                if event_type == "modified"
                else 1
                if event_type == "moved"
                else 2
                if event_type == "deleted"
                else 3
                if event_type == "created"
                else None
            )
        self.event_type = event_type
        # add src_file if not exists
        self.src_file = session.query(File).filter_by(path=src_path).first()
        if self.src_file is None:
            self.src_file = File(src_path)
            session.add(self.src_file)
        # add dest_file if not exists
        if dest_path is not None:
            self.dest_file = session.query(File).filter_by(path=dest_path).first()
            if self.dest_file is None:
                self.dest_file = File(dest_path)
                session.add(self.dest_file)
        # handle remove
        if event_type == 2:
            self.src_file.exists = False
        # handle create
        if event_type == 3:
            self.src_file.exists = True
        # turn files into path
        self.src_file = self.src_file.id
        if self.dest_file is not None:
            self.dest_file = self.dest_file.id

    def __repr__(self) -> str:
        return f"<{self.__tablename__}: {self.__dict__}>"
