import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class WifeRecord:
    user_id: str
    wife_id: str
    wife_name: str
    timestamp: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "WifeRecord":
        return cls(
            user_id=data["user_id"],
            wife_id=data["wife_id"],
            wife_name=data["wife_name"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "wife_id": self.wife_id,
            "wife_name": self.wife_name,
            "timestamp": self.timestamp.isoformat(),
        }


class WifeRecordStore:
    def __init__(self, data_dir: Path):
        self.file = data_dir / "wife_records.json"
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.file.exists():
            return {"date": "", "groups": {}}
        try:
            with self.file.open(encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"date": "", "groups": {}}

    def save(self) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        with self.file.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def today_str() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def ensure_today(self) -> None:
        if self.data.get("date") != self.today_str():
            self.reset_today()

    def reset_today(self) -> None:
        self.data = {"date": self.today_str(), "groups": {}}
        self.save()

    def get_user_today_count(self, group_id: str, user_id: str) -> int:
        self.ensure_today()
        return sum(
            1 for r in self._iter_group_records(group_id) if r.user_id == user_id
        )

    def list_user_records(self, group_id: str, user_id: str) -> list[WifeRecord]:
        self.ensure_today()
        return [r for r in self._iter_group_records(group_id) if r.user_id == user_id]

    def add_record(self, group_id: str, record: WifeRecord) -> None:
        self.ensure_today()

        group = self.data["groups"].setdefault(group_id, {"records": []})
        group["records"].append(record.to_dict())
        self.save()

    def _iter_group_records(self, group_id: str):
        records = self.data.get("groups", {}).get(group_id, {}).get("records", [])
        for raw in records:
            yield WifeRecord.from_dict(raw)
