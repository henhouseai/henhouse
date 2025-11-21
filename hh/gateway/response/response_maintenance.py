from __future__ import annotations

from hh.gateway.response.response import Response


class ResponseMaintenance(Response):
    """
    Lightweight response handler for the maintenance backend.
    Produces plain JSON suitable for machine consumption.
    """

    def __init__(self):
        super().__init__()
        self.payload = {"status": "ok", "data": None, "errors": None, "debug": None}

    def set_action_response(self, data: dict) -> None:
        super().set_action_response(data)
        self.payload["data"] = data

    def set_error_output(self, errors: dict) -> None:
        self.error_output = errors
        self.payload["errors"] = errors

    def set_debug_output(self, debug: dict) -> None:
        self.debug_output = debug
        self.payload["debug"] = debug

    def get_output(self) -> str:
        import json

        base_payload = dict(self.payload)
        if self.error_output:
            base_payload["status"] = "error"
        if base_payload.get("errors") is None:
            base_payload.pop("errors", None)
        if base_payload.get("debug") is None:
            base_payload.pop("debug", None)
        return json.dumps(base_payload, ensure_ascii=False)

