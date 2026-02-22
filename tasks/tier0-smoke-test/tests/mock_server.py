#!/usr/bin/env python3
"""Mock LLM HTTP server for attractorbench conformance testing.

Listens on port 9999 and returns canned responses for OpenAI, Anthropic, and Gemini API formats.
"""

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

OPENAI_CHAT_RESPONSE = {
    "id": "resp_mock_001",
    "object": "response",
    "created": 1700000000,
    "model": "gpt-4o",
    "output": [
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Hello! This is a mock response from the LLM."}],
        }
    ],
    "usage": {
        "input_tokens": 10,
        "output_tokens": 15,
        "total_tokens": 25,
    },
}

OPENAI_TOOL_RESPONSE = {
    "id": "resp_mock_002",
    "object": "response",
    "created": 1700000000,
    "model": "gpt-4o",
    "output": [
        {
            "type": "function_call",
            "call_id": "call_mock_001",
            "name": "get_weather",
            "arguments": json.dumps({"location": "San Francisco"}),
        }
    ],
    "usage": {"input_tokens": 20, "output_tokens": 25, "total_tokens": 45},
}

ANTHROPIC_RESPONSE = {
    "id": "msg_mock_001",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "Hello! This is a mock response from the LLM."}],
    "model": "claude-sonnet-4-20250514",
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 10, "output_tokens": 15},
}

ANTHROPIC_TOOL_RESPONSE = {
    "id": "msg_mock_002",
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "tool_use",
            "id": "toolu_mock_001",
            "name": "get_weather",
            "input": {"location": "San Francisco"},
        }
    ],
    "model": "claude-sonnet-4-20250514",
    "stop_reason": "tool_use",
    "usage": {"input_tokens": 20, "output_tokens": 25},
}

GEMINI_RESPONSE = {
    "candidates": [
        {
            "content": {
                "parts": [{"text": "Hello! This is a mock response from the LLM."}],
                "role": "model",
            },
            "finishReason": "STOP",
        }
    ],
    "usageMetadata": {
        "promptTokenCount": 10,
        "candidatesTokenCount": 15,
        "totalTokenCount": 25,
    },
}

MODELS_RESPONSE = {
    "object": "list",
    "data": [
        {"id": "gpt-4o", "object": "model", "owned_by": "openai"},
        {"id": "gpt-4o-mini", "object": "model", "owned_by": "openai"},
    ],
}

OPENAI_STREAM_EVENTS = [
    {"type": "response.created", "response": {"id": "resp_mock_stream", "status": "in_progress"}},
    {"type": "response.output_item.added", "output_index": 0, "item": {"type": "message", "role": "assistant"}},
    {"type": "response.content_part.added", "output_index": 0, "content_index": 0, "part": {"type": "output_text", "text": ""}},
    {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "delta": "Hello! "},
    {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "delta": "This is "},
    {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "delta": "a mock "},
    {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "delta": "streamed response."},
    {"type": "response.output_text.done", "output_index": 0, "content_index": 0, "text": "Hello! This is a mock streamed response."},
    {"type": "response.content_part.done", "output_index": 0, "content_index": 0, "part": {"type": "output_text", "text": "Hello! This is a mock streamed response."}},
    {"type": "response.output_item.done", "output_index": 0, "item": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Hello! This is a mock streamed response."}]}},
    {"type": "response.completed", "response": {"id": "resp_mock_stream", "status": "completed", "output": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Hello! This is a mock streamed response."}]}], "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}}},
]

ANTHROPIC_STREAM_EVENTS = [
    {"type": "message_start", "message": {"id": "msg_mock_stream", "type": "message", "role": "assistant", "content": [], "model": "claude-sonnet-4-20250514", "usage": {"input_tokens": 10, "output_tokens": 0}}},
    {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
    {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello! "}},
    {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "This is "}},
    {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "a mock "}},
    {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "streamed response."}},
    {"type": "content_block_stop", "index": 0},
    {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 20}},
    {"type": "message_stop"},
]


class MockHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress logging

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_sse(self, events):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        for event in events:
            line = f"data: {json.dumps(event)}\n\n"
            self.wfile.write(line.encode())
            self.wfile.flush()

    def do_GET(self):
        if self.path == "/v1/models" or self.path == "/models":
            self._send_json(MODELS_RESPONSE)
        elif self.path == "/health":
            self._send_json({"status": "ok"})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        want_stream = data.get("stream", False)

        # OpenAI Responses API
        if self.path in ("/v1/responses",):
            if want_stream:
                self._send_sse(OPENAI_STREAM_EVENTS)
            elif data.get("tools"):
                self._send_json(OPENAI_TOOL_RESPONSE)
            else:
                self._send_json(OPENAI_CHAT_RESPONSE)

        # OpenAI Chat Completions (legacy)
        elif self.path in ("/v1/chat/completions",):
            if want_stream:
                self._send_sse(OPENAI_STREAM_EVENTS)
            elif data.get("tools"):
                self._send_json(OPENAI_TOOL_RESPONSE)
            else:
                self._send_json(OPENAI_CHAT_RESPONSE)

        # Anthropic Messages API
        elif self.path in ("/v1/messages", "/messages"):
            if want_stream:
                self._send_sse(ANTHROPIC_STREAM_EVENTS)
            elif data.get("tools"):
                self._send_json(ANTHROPIC_TOOL_RESPONSE)
            else:
                self._send_json(ANTHROPIC_RESPONSE)

        # Gemini API
        elif "generateContent" in self.path:
            self._send_json(GEMINI_RESPONSE)
        elif "streamGenerateContent" in self.path:
            # Gemini streaming returns array
            self._send_json([GEMINI_RESPONSE])

        # Rate limit test endpoint
        elif self.path == "/v1/rate-limited":
            self.send_response(429)
            self.send_header("Content-Type", "application/json")
            self.send_header("Retry-After", "1")
            body = json.dumps({"error": {"message": "Rate limited", "type": "rate_limit_error"}}).encode()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        # Auth error test endpoint
        elif self.path == "/v1/auth-error":
            self._send_json({"error": {"message": "Invalid API key", "type": "authentication_error"}}, 401)

        else:
            self._send_json({"error": f"Unknown path: {self.path}"}, 404)


if __name__ == "__main__":
    port = 9999
    server = HTTPServer(("0.0.0.0", port), MockHandler)
    print(f"Mock LLM server listening on port {port}", file=sys.stderr)
    server.serve_forever()
