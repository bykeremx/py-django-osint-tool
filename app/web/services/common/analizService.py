# Analiz kaydetme: tam JSON rapor + elle eklenen maddeler.
from __future__ import annotations

import json
from typing import Any

from core.models import Analiz, AnalizItem

MAX_VALUE_LEN = 16_384


class AnalizService:
    @classmethod
    def save(
        cls,
        *,
        module: str,
        target: str,
        report: dict[str, Any],
        note: str = "",
        items: list[dict[str, str]] | None = None,
    ) -> Analiz:
        target = (target or "unknown").strip()[:255]
        note = (note or "").strip()
        clean = cls._to_json_safe(report)

        payload = {
            "module": module,
            "target": target,
            "analyst_note": note,
            "report": clean,
        }

        analiz = Analiz.objects.create(
            target=target,
            module=module,
            analyst_note=note,
            report_json=payload,
        )

        cls._create_items(analiz, items or [])
        return analiz

    @classmethod
    def add_item(cls, analiz: Analiz, key: str, value: str) -> AnalizItem:
        key = (key or "").strip()
        value = (value or "").strip()
        if not key:
            raise ValueError("Key boş olamaz.")
        if not value:
            raise ValueError("Value / bulgu metni boş olamaz.")
        return AnalizItem.objects.create(
            analiz=analiz,
            key=key[:512],
            value=value[:MAX_VALUE_LEN],
        )

    @classmethod
    def delete_item(cls, item_id: int, analiz_id: int) -> bool:
        deleted, _ = AnalizItem.objects.filter(pk=item_id, analiz_id=analiz_id).delete()
        return deleted > 0

    @classmethod
    def export_dict(cls, analiz: Analiz) -> dict[str, Any]:
        data = dict(analiz.report_json or {})
        data["analiz_id"] = analiz.pk
        data["created_at"] = analiz.created_at.isoformat()
        if analiz.analyst_note and not data.get("analyst_note"):
            data["analyst_note"] = analiz.analyst_note
        data["items"] = [
            {"id": item.pk, "key": item.key, "value": item.value}
            for item in analiz.items.all().order_by("id")
        ]
        return data

    @classmethod
    def _create_items(cls, analiz: Analiz, items: list[dict[str, str]]) -> None:
        rows: list[AnalizItem] = []
        for raw in items:
            key = (raw.get("key") or "").strip()
            value = (raw.get("value") or "").strip()
            if not key or not value:
                continue
            rows.append(
                AnalizItem(
                    analiz=analiz,
                    key=key[:512],
                    value=value[:MAX_VALUE_LEN],
                )
            )
        if rows:
            AnalizItem.objects.bulk_create(rows)

    @staticmethod
    def _to_json_safe(value: Any) -> Any:
        return json.loads(json.dumps(value, default=str, ensure_ascii=False))
