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

        # Check if error_output is set (indicates error mode) - modeled after MCP
        if self.error_output and "errors" in self.error_output:
            # Format error response using pre-set error data
            error_response = {
                "status": "error",
                "data": None,
                "errors": self.error_output["errors"]
            }
            if self.debug_output:
                error_response["debug"] = self.debug_output
            return json.dumps(error_response, ensure_ascii=False)

        # Success response
        base_payload = dict(self.payload)
        if base_payload.get("errors") is None:
            base_payload.pop("errors", None)
        if base_payload.get("debug") is None:
            base_payload.pop("debug", None)
        return json.dumps(base_payload, ensure_ascii=False)

