import json
import tempfile
import unittest
from pathlib import Path

from server import read_session_updates


SID = "11111111-2222-3333-4444-555555555555"


def event(kind, text="", index=0):
    update = {
        "sessionUpdate": kind,
        "content": {"type": "text", "text": text},
    }
    if kind.startswith("tool_call"):
        update.update(
            {
                "toolCallId": f"tool-{index}",
                "title": f"command {index}",
                "status": "completed",
            }
        )
    return {
        "method": "session/update",
        "params": {"sessionId": SID, "update": update},
    }


def kinds(events):
    return [((item.get("params") or {}).get("update") or {}).get("sessionUpdate") for item in events]


def texts(events):
    return [str((((item.get("params") or {}).get("update") or {}).get("content") or {}).get("text") or "") for item in events]


class HistoryMessagePriority(unittest.TestCase):
    def write_history(self, rows):
        temp = tempfile.TemporaryDirectory()
        path = Path(temp.name) / "updates.jsonl"
        path.write_text(
            "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
            encoding="utf-8",
        )
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def test_tool_flood_keeps_user_and_agent_messages(self):
        rows = []
        for turn in range(10):
            rows.append(event("user_message_chunk", f"older user {turn}"))
            rows.append(event("agent_message_chunk", f"older answer {turn}"))
        rows.append(event("user_message_chunk", "latest user prompt"))
        rows.extend(event("agent_thought_chunk", f"thought {i}", i) for i in range(40))
        rows.extend(event("tool_call", "", i) for i in range(35))
        rows.extend(event("agent_message_chunk", f"answer-{i} ", i) for i in range(15))

        got, meta = read_session_updates(self.write_history(rows), limit=50, chat_only=True)
        got_kinds = kinds(got)
        got_text = "\n".join(texts(got))

        self.assertLessEqual(len(got), 50)
        self.assertIn("user_message_chunk", got_kinds)
        self.assertIn("agent_message_chunk", got_kinds)
        self.assertIn("latest user prompt", got_text)
        self.assertIn("answer-14", got_text)
        self.assertFalse(meta["has_more"])

    def test_raw_event_count_does_not_stop_scan_before_prompt(self):
        rows = []
        for turn in range(24):
            rows.append(event("user_message_chunk", f"user {turn}"))
            rows.append(event("agent_message_chunk", f"answer {turn}"))
        rows.append(event("user_message_chunk", "prompt before flood"))
        rows.extend(event("tool_call", "", i) for i in range(240))
        rows.append(event("agent_message_chunk", "answer after flood"))

        got, _ = read_session_updates(self.write_history(rows), limit=50, chat_only=True)
        got_text = "\n".join(texts(got))

        self.assertIn("prompt before flood", got_text)
        self.assertIn("answer after flood", got_text)

    def test_history_pages_do_not_overlap(self):
        rows = []
        for turn in range(80):
            rows.append(event("user_message_chunk", f"user {turn}"))
            rows.append(event("agent_message_chunk", f"answer {turn}"))
        session_dir = self.write_history(rows)

        page_one, meta_one = read_session_updates(session_dir, limit=20, chat_only=True)
        page_two, meta_two = read_session_updates(
            session_dir,
            limit=20,
            before_bytes=meta_one["older_before"],
            chat_only=True,
        )

        self.assertTrue(meta_one["has_more"])
        self.assertLess(meta_two["older_before"], meta_one["older_before"])
        self.assertTrue(set(texts(page_one)).isdisjoint(texts(page_two)))

    def test_live_tail_prioritizes_messages_over_tools(self):
        rows = [event("user_message_chunk", "live user")]
        rows.extend(event("tool_call", "", i) for i in range(250))
        rows.append(event("agent_message_chunk", "live answer"))

        got, meta = read_session_updates(
            self.write_history(rows),
            limit=20,
            max_bytes=2_000_000,
            live=True,
        )
        got_text = "\n".join(texts(got))

        self.assertIn("live user", got_text)
        self.assertIn("live answer", got_text)
        self.assertTrue(meta["live"])
        self.assertLessEqual(len(got), 20)


if __name__ == "__main__":
    unittest.main()
