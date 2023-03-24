from json import load
from pathlib import Path
import os

from .models import add_event

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
        self.db = db

    def on_any_event(self, event):
        if type(event) in [
            FileModifiedEvent,
            FileMovedEvent,
            FileDeletedEvent,
            FileCreatedEvent,
        ]:
            add_event(event, self.db.session())


class Collector:
    def __init__(self, db) -> None:
        self.paths = load(open(SYNC_PATH, "r"))
        self.observer = Observer()
        for path in self.paths:
            if os.path.exists(path):
                self.observer.schedule(EventHandler(db), path, recursive=True)

    def run(self) -> None:
        self.observer.start()
