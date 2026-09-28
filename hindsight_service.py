"""
Thin wrapper around the Hindsight client for the Meeting Prep Agent.

Design: one Hindsight memory bank per contact (bank_id = slugified contact
name). Every logged meeting is retained into that contact's bank, tagged
with the date it actually happened. Prepping for a meeting calls reflect()
on that bank, which lets Hindsight pull in everything it has consolidated
about that person - past topics, promises, tone - and turn it into a
natural-language briefing.

A small local contacts.json tracks which contacts we've created banks for,
plus lightweight local fields (meeting count, next meeting date) that the
UI needs but that don't belong in Hindsight itself.
"""

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from hindsight_client import Hindsight

DATA_DIR = Path(__file__).parent / "data"
CONTACTS_FILE = DATA_DIR / "contacts.json"
_lock = threading.Lock()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return f"contact-{slug}" or "contact-unknown"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_contacts() -> dict:
    if not CONTACTS_FILE.exists():
        return {}
    with open(CONTACTS_FILE, "r") as f:
        return json.load(f)


def _save_contacts(contacts: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with open(CONTACTS_FILE, "w") as f:
        json.dump(contacts, f, indent=2)


class MeetingPrepAgent:
    def __init__(self, base_url: str, api_key: str | None = None):
        self._base_url = base_url
        self._api_key = api_key

    def _client(self) -> Hindsight:
        # A fresh client per call, rather than one shared instance for the
        # app's whole lifetime. The SDK's async HTTP client ties its
        # internal timeout/connection state to the event loop that was
        # active when it was created; reusing one client across separate
        # sync-to-async calls (as Flask does, once per request) causes
        # "Timeout context manager should be used inside a task" once the
        # original loop is gone. Creating a new client per call sidesteps
        # that entirely, at the small cost of a new connection each time.
        return Hindsight(base_url=self._base_url, api_key=self._api_key, timeout=60.0)

    # ---- contacts -----------------------------------------------------

    def list_contacts(self) -> list[dict]:
        contacts = _load_contacts()
        result = []
        for c in contacts.values():
            # backfill the field for contacts created before this existed
            c.setdefault("next_meeting_date", None)
            result.append(c)
        return sorted(result, key=lambda c: c["name"].lower())

    def get_or_create_contact(self, name: str) -> dict:
        with _lock:
            contacts = _load_contacts()
            bank_id = _slugify(name)
            if bank_id not in contacts:
                try:
                    self._client().create_bank(
                        bank_id=bank_id,
                        name=f"Meeting memory: {name}",
                        mission=(
                            f"I track every meeting and interaction with {name}. "
                            "I remember what was discussed, promises made on either "
                            "side, open follow-ups, and the general tone of the "
                            "relationship, so I can brief someone before their next "
                            "meeting with this person."
                        ),
                        disposition={"skepticism": 2, "literalism": 4, "empathy": 4},
                    )
                except Exception:
                    pass
                contacts[bank_id] = {
                    "bank_id": bank_id,
                    "name": name,
                    "created_at": _now_iso(),
                    "meeting_count": 0,
                    "next_meeting_date": None,
                }
                _save_contacts(contacts)
            contacts[bank_id].setdefault("next_meeting_date", None)
            return contacts[bank_id]

    def _bump_meeting_count(self, bank_id: str) -> None:
        with _lock:
            contacts = _load_contacts()
            if bank_id in contacts:
                contacts[bank_id]["meeting_count"] += 1
                contacts[bank_id]["last_meeting_at"] = _now_iso()
                _save_contacts(contacts)

    def set_next_meeting(self, contact_name: str, date_str: str | None) -> dict:
        """date_str is a plain YYYY-MM-DD string from an <input type=date>,
        or None/"" to clear the reminder."""
        contact = self.get_or_create_contact(contact_name)
        with _lock:
            contacts = _load_contacts()
            contacts[contact["bank_id"]]["next_meeting_date"] = date_str or None
            _save_contacts(contacts)
            return contacts[contact["bank_id"]]

    # ---- core actions ---------------------------------------------------

    def log_meeting(self, contact_name: str, notes: str, meeting_date: str | None = None) -> dict:
        """Retain a meeting note into that contact's memory bank, tagged
        with the date the meeting actually happened (defaults to now)."""
        contact = self.get_or_create_contact(contact_name)
        if meeting_date:
            # Store at midday UTC on the chosen date so it sorts correctly
            # without timezone edge cases shifting it to the wrong day.
            timestamp = f"{meeting_date}T12:00:00+00:00"
        else:
            timestamp = _now_iso()

        self._client().retain(
            bank_id=contact["bank_id"],
            content=notes,
            context="meeting notes",
            timestamp=timestamp,
        )
        self._bump_meeting_count(contact["bank_id"])
        return {"contact": contact, "logged": True, "meeting_date": meeting_date}

    def prep_briefing(self, contact_name: str) -> dict:
        """Generate a meeting-prep briefing using reflect()."""
        contact = self.get_or_create_contact(contact_name)
        answer = self._client().reflect(
            bank_id=contact["bank_id"],
            query=(
                "I'm about to have a meeting with this person. Give me a prep "
                "briefing: what have we discussed before, what promises or "
                "action items are still open on either side, and anything "
                "about tone or relationship context I should keep in mind. "
                "If this is our first meeting, say so plainly."
            ),
            context="meeting prep",
            budget="mid",
        )
        return {"contact": contact, "briefing": answer.text}

    def timeline(self, contact_name: str) -> dict:
        """Raw recall of everything remembered about this contact, for the
        'show the memory' panel in the UI."""
        contact = self.get_or_create_contact(contact_name)
        results = self._client().recall(
            bank_id=contact["bank_id"],
            query="everything discussed, promised, or notable about this person",
            budget="high",
            max_tokens=4096,
        )
        memories = [
            {"text": r.text, "type": getattr(r, "type", None)}
            for r in results.results
        ]
        return {"contact": contact, "memories": memories}
