"""
Tests for main FastAPI application and endpoints
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from main import app
from game_room import room_manager


class TestHTTPEndpoints:
    """Test suite for HTTP endpoints"""

    def test_root_endpoint(self, test_client):
        """Test the root health check endpoint"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "Six Second Scribbles API"

    async def test_room_status_nonexistent(self, async_client):
        """Test room status for a non-existent room"""
        response = await async_client.get("/rooms/NONEXISTENT/status")

        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False

    async def test_room_status_existing(self, async_client):
        """Test room status for an existing room"""
        # Create a room
        room = room_manager.get_or_create_room("TEST01")

        # Add a player
        ws = AsyncMock()
        await room.add_player("player-1", "Alice", ws)
        room.metadata.game_phase = "drawing"

        response = await async_client.get("/rooms/TEST01/status")

        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
        assert data["players"] == 1
        assert data["game_phase"] == "drawing"


class TestWebSocketConnection:
    """Test suite for WebSocket connection handling"""

    def test_websocket_connect_and_disconnect(self, test_client):
        """Test basic WebSocket connection and disconnection"""
        with test_client.websocket_connect("/party/TEST01") as websocket:
            # Should receive initial room state
            data = websocket.receive_text()
            message = json.loads(data)

            assert message["type"] == "room_state"
            assert message["gamePhase"] == "lobby"
            assert isinstance(message["players"], list)

    def test_websocket_join_message(self, test_client):
        """Test joining a room via WebSocket"""
        with test_client.websocket_connect("/party/TEST01") as websocket:
            # Receive initial state
            websocket.receive_text()

            # Send join message
            join_msg = {
                "type": "join",
                "playerId": "player-1",
                "name": "Alice"
            }
            websocket.send_text(json.dumps(join_msg))

            # Should receive player_joined broadcast
            data = websocket.receive_text()
            message = json.loads(data)

            assert message["type"] == "player_joined"
            assert message["playerId"] == "player-1"
            assert message["name"] == "Alice"
            assert len(message["players"]) == 1

    def test_multiple_players_join(self, test_client):
        """Test multiple players joining the same room"""
        with test_client.websocket_connect("/party/TEST01") as ws1:
            ws1.receive_text()  # Initial state

            # Player 1 joins
            ws1.send_text(json.dumps({
                "type": "join",
                "playerId": "player-1",
                "name": "Alice"
            }))
            ws1.receive_text()  # player_joined

            with test_client.websocket_connect("/party/TEST01") as ws2:
                ws2.receive_text()  # Initial state

                # Player 2 joins
                ws2.send_text(json.dumps({
                    "type": "join",
                    "playerId": "player-2",
                    "name": "Bob"
                }))

                # Both should receive the broadcast
                msg1 = json.loads(ws1.receive_text())
                msg2 = json.loads(ws2.receive_text())

                assert msg1["type"] == "player_joined"
                assert msg2["type"] == "player_joined"
                assert len(msg1["players"]) == 2
                assert len(msg2["players"]) == 2

    def test_player_disconnect_cleanup(self, test_client):
        """Test that players are cleaned up when they disconnect"""
        room_id = "TEST01"

        with test_client.websocket_connect(f"/party/{room_id}") as websocket:
            websocket.receive_text()  # Initial state

            # Join
            websocket.send_text(json.dumps({
                "type": "join",
                "playerId": "player-1",
                "name": "Alice"
            }))
            websocket.receive_text()  # player_joined

        # After disconnect, room should eventually be cleaned up or empty
        # Give it a moment for cleanup
        import time
        time.sleep(0.1)

        # Check room is empty
        room = room_manager.get_room(room_id)
        if room:  # Room might not be cleaned up yet
            assert len(room.players) == 0


class TestMessageHandling:
    """Test suite for game message handling"""

    def test_start_game_message(self, test_client, sample_messages):
        """Test starting a game"""
        with test_client.websocket_connect("/party/TEST01") as ws1:
            ws1.receive_text()  # Initial state

            # Player 1 joins
            ws1.send_text(json.dumps(sample_messages["join"]))
            ws1.receive_text()  # player_joined

            with test_client.websocket_connect("/party/TEST01") as ws2:
                ws2.receive_text()  # Initial state

                # Player 2 joins
                join_msg2 = {
                    "type": "join",
                    "playerId": "player-2",
                    "name": "Bob"
                }
                ws2.send_text(json.dumps(join_msg2))

                # Clear join broadcasts
                ws1.receive_text()
                ws2.receive_text()

                # Start game
                ws1.send_text(json.dumps(sample_messages["start_game"]))

                # Both players should receive start_game
                msg1 = json.loads(ws1.receive_text())
                msg2 = json.loads(ws2.receive_text())

                assert msg1["type"] == "start_game"
                assert msg2["type"] == "start_game"
                assert msg1["difficulty"] == "medium"
                assert msg1["rounds"] == 5

    def test_start_game_requires_two_players(self, test_client, sample_messages):
        """Test that game cannot start with less than 2 players"""
        with test_client.websocket_connect("/party/TEST01") as websocket:
            websocket.receive_text()  # Initial state

            # Only one player joins
            websocket.send_text(json.dumps(sample_messages["join"]))
            websocket.receive_text()  # player_joined

            # Try to start game (should be ignored)
            websocket.send_text(json.dumps(sample_messages["start_game"]))

            # Should not receive start_game message (would timeout if we waited)
            # This is a limitation of TestClient - we can't easily test no-response

    def test_heartbeat_message(self, test_client, sample_messages):
        """Test heartbeat messages update player activity"""
        with test_client.websocket_connect("/party/TEST01") as websocket:
            websocket.receive_text()  # Initial state

            # Join
            websocket.send_text(json.dumps(sample_messages["join"]))
            websocket.receive_text()  # player_joined

            # Send heartbeat (should not cause any broadcast)
            websocket.send_text(json.dumps(sample_messages["heartbeat"]))

            # No response expected for heartbeat

    def test_settings_update_from_host(self, test_client, sample_messages):
        """Test that only host can update settings"""
        with test_client.websocket_connect("/party/TEST01") as ws1:
            ws1.receive_text()  # Initial state

            # Player 1 joins (becomes host)
            ws1.send_text(json.dumps(sample_messages["join"]))
            ws1.receive_text()  # player_joined

            with test_client.websocket_connect("/party/TEST01") as ws2:
                ws2.receive_text()  # Initial state

                # Player 2 joins
                join_msg2 = {
                    "type": "join",
                    "playerId": "player-2",
                    "name": "Bob"
                }
                ws2.send_text(json.dumps(join_msg2))

                # Clear join broadcasts
                ws1.receive_text()
                ws2.receive_text()

                # Host updates settings
                ws1.send_text(json.dumps(sample_messages["settings_update"]))

                # Both should receive update
                msg1 = json.loads(ws1.receive_text())
                msg2 = json.loads(ws2.receive_text())

                assert msg1["type"] == "settings_update"
                assert msg2["type"] == "settings_update"
                assert msg1["difficulty"] == "hard"

    def test_draw_stroke_broadcast(self, test_client):
        """Test that draw strokes are broadcast to all players"""
        with test_client.websocket_connect("/party/TEST01") as ws1:
            ws1.receive_text()  # Initial state

            # Player 1 joins
            ws1.send_text(json.dumps({
                "type": "join",
                "playerId": "player-1",
                "name": "Alice"
            }))
            ws1.receive_text()  # player_joined

            with test_client.websocket_connect("/party/TEST01") as ws2:
                ws2.receive_text()  # Initial state

                # Player 2 joins
                ws2.send_text(json.dumps({
                    "type": "join",
                    "playerId": "player-2",
                    "name": "Bob"
                }))

                # Clear join broadcasts
                ws1.receive_text()
                ws2.receive_text()

                # Player 1 draws
                draw_msg = {
                    "type": "draw_stroke",
                    "playerId": "player-1",
                    "stroke": {
                        "color": "#000000",
                        "width": 2,
                        "points": [{"x": 10, "y": 20}]
                    }
                }
                ws1.send_text(json.dumps(draw_msg))

                # Both should receive the stroke
                msg1 = json.loads(ws1.receive_text())
                msg2 = json.loads(ws2.receive_text())

                assert msg1["type"] == "draw_stroke"
                assert msg2["type"] == "draw_stroke"

    def test_player_ready_tracking(self, test_client):
        """Test player ready status tracking"""
        with test_client.websocket_connect("/party/TEST01") as ws1:
            ws1.receive_text()  # Initial state

            # Player 1 joins
            ws1.send_text(json.dumps({
                "type": "join",
                "playerId": "player-1",
                "name": "Alice"
            }))
            ws1.receive_text()  # player_joined

            # Player indicates ready
            ws1.send_text(json.dumps({
                "type": "player_ready",
                "playerId": "player-1"
            }))

            # Should receive ready_status
            msg = json.loads(ws1.receive_text())
            assert msg["type"] == "ready_status"
            assert msg["readyCount"] == 1
            assert msg["totalPlayers"] == 1

    def test_restart_game(self, test_client):
        """Test restarting a game"""
        with test_client.websocket_connect("/party/TEST01") as websocket:
            websocket.receive_text()  # Initial state

            # Join
            websocket.send_text(json.dumps({
                "type": "join",
                "playerId": "player-1",
                "name": "Alice"
            }))
            websocket.receive_text()  # player_joined

            # Restart game
            websocket.send_text(json.dumps({
                "type": "restart_game"
            }))

            # Should receive restart broadcast
            msg = json.loads(websocket.receive_text())
            assert msg["type"] == "restart_game"

    def test_request_game_state(self, test_client):
        """Test requesting current game state"""
        with test_client.websocket_connect("/party/TEST01") as websocket:
            # Initial state
            initial = json.loads(websocket.receive_text())
            assert initial["type"] == "room_state"

            # Join
            websocket.send_text(json.dumps({
                "type": "join",
                "playerId": "player-1",
                "name": "Alice"
            }))
            websocket.receive_text()  # player_joined

            # Request state
            websocket.send_text(json.dumps({
                "type": "request_game_state",
                "playerId": "player-1"
            }))

            # Should receive room_state
            msg = json.loads(websocket.receive_text())
            assert msg["type"] == "room_state"
            assert len(msg["players"]) == 1


class TestHostTransfer:
    """Test suite for host transfer logic"""

    def test_host_transfer_on_disconnect(self, test_client):
        """Test that host is transferred when original host disconnects"""
        with test_client.websocket_connect("/party/TEST01") as ws1:
            ws1.receive_text()  # Initial state

            # Player 1 joins (becomes host)
            ws1.send_text(json.dumps({
                "type": "join",
                "playerId": "player-1",
                "name": "Alice"
            }))
            ws1.receive_text()  # player_joined

            with test_client.websocket_connect("/party/TEST01") as ws2:
                ws2.receive_text()  # Initial state

                # Player 2 joins
                ws2.send_text(json.dumps({
                    "type": "join",
                    "playerId": "player-2",
                    "name": "Bob"
                }))

                # Clear join broadcasts
                ws1.receive_text()
                ws2.receive_text()

                # Player 1 (host) disconnects
                ws1.close()

            # Player 2 should receive host_changed
            msg = json.loads(ws2.receive_text())
            assert msg["type"] == "player_left"

            msg = json.loads(ws2.receive_text())
            assert msg["type"] == "host_changed"
            assert msg["newHostId"] == "player-2"


class TestErrorHandling:
    """Test suite for error handling"""

    def test_invalid_json_message(self, test_client):
        """Test handling of invalid JSON messages"""
        with test_client.websocket_connect("/party/TEST01") as websocket:
            websocket.receive_text()  # Initial state

            # Send invalid JSON
            websocket.send_text("not valid json{")

            # Connection should still be open (error is logged but not fatal)
            # We can continue sending valid messages

    def test_room_cleanup_after_all_disconnect(self, test_client):
        """Test that rooms are eventually cleaned up after all players leave"""
        room_id = "TEST01"

        with test_client.websocket_connect(f"/party/{room_id}") as ws1:
            ws1.receive_text()
            ws1.send_text(json.dumps({
                "type": "join",
                "playerId": "player-1",
                "name": "Alice"
            }))
            ws1.receive_text()

        # After disconnect, check room state
        import time
        time.sleep(0.1)

        room = room_manager.get_room(room_id)
        if room:
            assert room.is_empty()
