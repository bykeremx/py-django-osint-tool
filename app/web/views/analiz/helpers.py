from typing import Any


def attach_analiz(context: dict, *, module: str, target: str, report: dict[str, Any] | None) -> dict:
    if not report:
        return context
    context["analiz_module"] = module
    context["analiz_target"] = target
    context["analiz_report"] = {
        "module": module,
        "target": target,
        "report": report,
    }
    return context
