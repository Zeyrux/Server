from pathlib import Path
from datetime import datetime

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import Session, relationship
from sqlalchemy.dialects.sqlite import INTEGER, VARCHAR, DATETIME, BOOLEAN


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

    def __init__(self, ip, last_sync: datetime = None) -> None:
        self.ip = ip
        self.last_sync = (
            last_sync if last_sync is not None else datetime(2000, 1, 1, 0, 0, 0, 0)
        )


class Change(Base):
    __tablename__ = "change"

    id = Column("id", INTEGER(), primary_key=True)
    id_file = Column("file", ForeignKey("file.id"), nullable=False)
    id_client = Column("client", ForeignKey("client.id"), nullable=False)
    time = Column("time", DATETIME, nullable=False)

    files = relationship("File", back_populates="file.id", lazy="dynamic")
    clients = relationship("Client", back_populates="change.id", lazy="dynamic")

    def __init__(self, file: "File", client: Client | int, time: datetime) -> None:
        self.id_file = file
        self.client = client
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

    def __init__(
        self,
        path: Path | str,
        size: int,
        change_date: datetime,
        exists: bool = True,
    ) -> None:
        self.path = str(path)
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

    src_file = relationship("File", back_populates="file.id", lazy="dynamic")
    dest_file = relationship("File", back_populates="file.id", lazy="dynamic")

    def __init__(
        self,
        session: Session,
        event_type: str,
        src_file: Path | str | int | File,
        dest_file: Path | str | int | File = None,
        time: datetime = datetime.now(),
    ) -> None:
        self.event_type = event_type
        self.time = time
        # add src_file if not exists
        if type(src_file) == File:
            self.id_src_file = src_file
        elif type(src_file) == int:
            self.id_src_file = session.query(File).filter_by(id=src_file).first()
        else:
            self.id_src_file = session.query(File).filter_by(path=str(src_file)).first()
        if self.id_src_file is None:
            self.id_src_file = File(src_file)
            session.add(self.id_src_file)
            session.commit()
        # add dest_file if not exists
        if dest_file is not None:
            if type(dest_file) == File:
                self.id_dest_file = dest_file
            elif type(dest_file) == int:
                self.id_dest_file = session.query(File).filter_by(id=dest_file).first()
            else:
                self.id_dest_file = (
                    session.query(File).filter_by(path=str(dest_file)).first()
                )
            if self.id_dest_file is None:
                self.id_dest_file = File(dest_file)
                session.add(self.id_dest_file)
                session.commit()
        # handle remove
        if event_type == EVENT_DELETED:
            self.id_src_file.exists = False
        # handle create
        if event_type == EVENT_CREATED:
            self.id_src_file.exists = True
        session.commit()
        # turn files into path
        self.id_src_file = self.id_src_file.id
        if self.id_dest_file is not None:
            self.id_dest_file = self.id_dest_file.id

    # @staticmethod
    # def from_event(session, event: "Event") -> "Event":
    #     return Event(
    #         session, event.type, event.ref_src_file, event.ref_dest_file, event.time
    #     )

    # @staticmethod
    # def from_other_db(
    #     session_new_event: Session,
    #     session_existing_event: Session,
    #     event: "Event",
    #     client: int,
    # ) -> "Event":
    #     return Event(
    #         session_new_event,
    #         client,
    #         event.event_type,
    #         event.src_path(session_existing_event),
    #         dest_file=event.dest_path(session_existing_event)
    #         if event.dest_file is not None
    #         else None,
    #         time=event.time,
    #     )

    # def src_path(self, session: Session) -> Path:
    #     return Path(self.get_src_file(session).path)

    # def dest_path(self, session: Session) -> Path:
    #     return Path(self.get_dest_file(session).path)

    # def get_src_file(self, session: Session) -> File:
    #     if self.src_file_obj is None:
    #         self.src_file_obj = (
    #             session.query(File).filter(File.id == self.src_file).first()
    #         )
    #     return self.src_file_obj

    # def get_dest_file(self, session: Session) -> File:
    #     if self.dest_file_obj is None:
    #         self.dest_file_obj = (
    #             session.query(File).filter(File.id == self.dest_file).first()
    #         )
    #     return self.dest_file_obj

    def __repr__(self) -> str:
        return f"<{self.__tablename__}: {self.__dict__}>"
