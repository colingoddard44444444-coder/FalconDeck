from datetime import datetime
from pathlib import Path


class EventEngine:
    def __init__(self, log_file, maximum_events=100):
        self.log_file = Path(log_file)
        self.maximum_events = maximum_events
        self.events = []
        self.listeners = []

        self.load()

    def subscribe(self, listener):
        if listener not in self.listeners:
            self.listeners.append(listener)

    def unsubscribe(self, listener):
        if listener in self.listeners:
            self.listeners.remove(listener)

    def publish(
        self,
        message,
        category="SYSTEM",
        importance="normal",
        data=None,
    ):
        message = str(message).strip()

        if not message:
            return None

        event = {
            "time": datetime.now().strftime("%H:%M"),
            "message": message,
            "category": str(category).upper(),
            "importance": str(importance).lower(),
            "data": data or {},
        }

        # Avoid immediately repeating the same event.
        if (
            self.events
            and self.events[0]["message"] == event["message"]
            and self.events[0]["category"] == event["category"]
        ):
            return self.events[0]

        self.events.insert(0, event)
        self.events = self.events[: self.maximum_events]

        self.save()

        for listener in tuple(self.listeners):
            try:
                listener(event)
            except Exception as error:
                print(
                    f"EVENT LISTENER ERROR: {error}",
                    flush=True,
                )

        return event

    def recent(self, limit=4):
        return self.events[: max(0, int(limit))]

    def format_event(self, event):
        return (
            f'{event["time"]}  '
            f'{event["message"]}'
        )

    def save(self):
        try:
            self.log_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            chronological = reversed(self.events)

            lines = []

            for event in chronological:
                lines.append(
                    "|".join(
                        (
                            event["time"],
                            event["category"],
                            event["importance"],
                            event["message"].replace(
                                "\n",
                                " ",
                            ),
                        )
                    )
                )

            self.log_file.write_text(
                "\n".join(lines) + ("\n" if lines else ""),
                encoding="utf-8",
            )

        except OSError as error:
            print(
                f"EVENT LOG SAVE ERROR: {error}",
                flush=True,
            )

    def load(self):
        if not self.log_file.exists():
            return

        loaded = []

        try:
            for line in self.log_file.read_text(
                encoding="utf-8"
            ).splitlines():
                parts = line.split("|", 3)

                if len(parts) == 4:
                    time_text, category, importance, message = parts
                else:
                    # Support the earlier Mission Activity format.
                    time_text = line[:5]
                    message = line[7:] if len(line) > 7 else line
                    category = "SYSTEM"
                    importance = "normal"

                loaded.append(
                    {
                        "time": time_text,
                        "message": message,
                        "category": category,
                        "importance": importance,
                        "data": {},
                    }
                )

            self.events = loaded[-self.maximum_events :][::-1]

        except OSError as error:
            print(
                f"EVENT LOG LOAD ERROR: {error}",
                flush=True,
            )
