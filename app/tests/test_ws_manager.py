"""Regression coverage for the process-wide WebSocket event relay."""

from app.core import ws_manager


def test_pubsub_listener_uses_idle_safe_dedicated_redis_connection(monkeypatch):
    captured = {}
    manager = ws_manager.ConnectionManager()

    class FakePubSub:
        def subscribe(self, channel):
            captured["channel"] = channel

        def get_message(self, *, timeout):
            captured["poll_timeout"] = timeout
            manager._listener_stop.set()
            return None

        def close(self):
            captured["pubsub_closed"] = True

    class FakeRedis:
        def pubsub(self, *, ignore_subscribe_messages):
            captured["ignore_subscribe_messages"] = ignore_subscribe_messages
            return FakePubSub()

        def close(self):
            captured["client_closed"] = True

    def fake_from_url(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeRedis()

    monkeypatch.setattr(ws_manager.redis.Redis, "from_url", fake_from_url)

    manager._listen_for_remote_events()

    assert captured["socket_timeout"] is None
    assert captured["socket_connect_timeout"] == 2
    assert captured["health_check_interval"] == 30
    assert captured["channel"] == ws_manager.WS_EVENTS_CHANNEL
    assert captured["poll_timeout"] == 1.0
    assert captured["ignore_subscribe_messages"] is True
    assert captured["pubsub_closed"] is True
    assert captured["client_closed"] is True
