from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from backend.config import TEMPLATES_FILE
from backend.logger import get_logger

log = get_logger(__name__)

_LOCK = threading.Lock()


@dataclass
class HashtagTemplate:
    name:     str
    hashtags: List[str] = field(default_factory=list)

    def formatted_text(self, separator: str = " ") -> str:
        return separator.join(self.hashtags)

    def as_dict(self) -> dict:
        return {"name": self.name, "hashtags": list(self.hashtags)}

    @classmethod
    def from_dict(cls, d: dict) -> "HashtagTemplate":
        return cls(name=str(d.get("name", "")), hashtags=list(d.get("hashtags", [])))


def _load_raw() -> dict:
    path: Path = TEMPLATES_FILE
    if not path.exists():
        return {"templates": []}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or "templates" not in data:
            log.warning("templates.json has unexpected structure — resetting")
            return {"templates": []}
        return data
    except (json.JSONDecodeError, OSError) as exc:
        log.error("Failed to read templates.json: %s", exc)
        return {"templates": []}


def _save_raw(data: dict) -> None:
    path: Path = TEMPLATES_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        tmp.replace(path)
        log.debug("templates.json saved (%d templates)", len(data.get("templates", [])))
    except OSError as exc:
        log.error("Failed to save templates.json: %s", exc)
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise


def list_templates() -> List[HashtagTemplate]:
    with _LOCK:
        data = _load_raw()
    return [HashtagTemplate.from_dict(t) for t in data.get("templates", [])]


def get_template(name: str) -> Optional[HashtagTemplate]:
    with _LOCK:
        data = _load_raw()
    for t in data.get("templates", []):
        if t.get("name") == name:
            return HashtagTemplate.from_dict(t)
    return None


def save_template(template: HashtagTemplate) -> None:
    with _LOCK:
        data = _load_raw()
        templates = data.get("templates", [])
        for i, t in enumerate(templates):
            if t.get("name") == template.name:
                templates[i] = template.as_dict()
                log.debug("Updated template '%s'", template.name)
                break
        else:
            templates.append(template.as_dict())
            log.debug("Added template '%s'", template.name)
        data["templates"] = templates
        _save_raw(data)


def delete_template(name: str) -> bool:
    with _LOCK:
        data = _load_raw()
        templates = data.get("templates", [])
        original_len = len(templates)
        data["templates"] = [t for t in templates if t.get("name") != name]
        if len(data["templates"]) == original_len:
            log.debug("delete_template: '%s' not found", name)
            return False
        _save_raw(data)
        log.debug("Deleted template '%s'", name)
        return True


def rename_template(old_name: str, new_name: str) -> bool:
    with _LOCK:
        data = _load_raw()
        templates = data.get("templates", [])
        names = [t.get("name") for t in templates]
        if old_name not in names:
            return False
        if new_name in names:
            return False
        for t in templates:
            if t.get("name") == old_name:
                t["name"] = new_name
                break
        data["templates"] = templates
        _save_raw(data)
        log.debug("Renamed template '%s' → '%s'", old_name, new_name)
        return True


def template_names() -> List[str]:
    with _LOCK:
        data = _load_raw()
    return [t.get("name", "") for t in data.get("templates", [])]


def ensure_default_templates() -> None:
    with _LOCK:
        data = _load_raw()
        if data.get("templates"):
            return
        data["templates"] = [
            {
                "name": "TikTok General",
                "hashtags": ["#fyp", "#foryou", "#foryoupage", "#viral", "#trending"],
            },
            {
                "name": "Gaming Clips",
                "hashtags": [
                    "#gaming", "#gamer", "#gamingclips", "#fyp",
                    "#ps5", "#xbox", "#pcgaming", "#viral",
                ],
            },
            {
                "name": "Lifestyle",
                "hashtags": [
                    "#lifestyle", "#daily", "#vlog", "#fyp",
                    "#aesthetic", "#mood", "#viral",
                ],
            },
        ]
        _save_raw(data)
        log.info("Default hashtag templates seeded")