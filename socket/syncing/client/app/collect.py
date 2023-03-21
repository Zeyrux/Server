from json import load
from pathlib import Path
import os

from .models_old import Event

from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileModifiedEvent,
    FileMovedEvent,
    FileDeletedEvent,
    FileCreatedEvent,
)


SYNC_PATH = Path("client", "sync.json")


class EventHandler(FileSystemEventHandler):
    def __init__(self, db) -> None:
        super().__init__()
        self.session = db.session()

    def on_any_event(self, event):
        if type(event) in [
            FileModifiedEvent,
            FileMovedEvent,
            FileDeletedEvent,
            FileCreatedEvent,
        ]:
            self.session.add(
                Event(
                    self.session,
                    event.event_type,
                    event.src_path,
                    dest_path=event.dest_path
                    if type(event) == FileMovedEvent
                    else None,
                )
            )
            self.session.commit()


class Collector:
    def __init__(self, db) -> None:
        self.paths = load(open(SYNC_PATH, "r"))
        self.observer = Observer()
        for path in self.paths:
            if os.path.exists(path):
                self.observer.schedule(EventHandler(db), path, recursive=True)

    def run(self) -> None:
        self.observer.start()
