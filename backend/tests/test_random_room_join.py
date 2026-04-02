"""Tests for random room join functionality"""

import json


class TestRandomRoomJoin:
    """Test suite for random room join feature"""

    def test_no_available_rooms(self, test_client):
        """Test when no public rooms are available"""
        response = test_client.get("/api/rooms/random")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "no available" in data["detail"].lower()

    def test_find_public_room(self, test_client):
        """Test finding a public room that's available"""
        room_id = "PUBLIC_ROOM_01"

        with test_client.websocket_connect(f"/party/{room_id}") as ws:
            ws.receive_text()  # room_state

            ws.send_text(json.dumps({"type": "join", "playerId": "player1", "name": "Test Player"}))
            ws.receive_text()  # player_joined

            response = test_client.get("/api/rooms/random")

            assert response.status_code == 200
            data = response.json()
            assert data["room_code"] == room_id
            assert data["player_count"] == 1
            assert data["max_players"] == 10

    def test_private_room_not_returned(self, test_client):
        """Test that private rooms are not returned in random join"""
        from app.game_room import room_manager

        room_id = "PRIVATE_ROOM"

        with test_client.websocket_connect(f"/party/{room_id}") as ws:
            ws.receive_text()  # room_state

            ws.send_text(json.dumps({"type": "join", "playerId": "host1", "name": "Host"}))
            ws.receive_text()  # player_joined

            # Set privacy directly — privacy_changed has no server ack, so a
            # bare send_text() would race with the following GET request.
            room = room_manager.get_room(room_id)
            assert room is not None
            room.metadata.is_private = True

            response = test_client.get("/api/rooms/random")
            assert response.status_code == 404

    def test_full_room_not_returned(self, test_client):
        """Test that full rooms (10 players) are not returned by random join."""
        from unittest.mock import AsyncMock

        from app.game_room import GameRoom, PlayerInfo, room_manager

        room_id = "FULL_ROOM"
        # Build the room without get_or_create_room (which needs an event loop
        # to create_task the idle check).
        room = GameRoom(room_id)
        for i in range(10):
            ws = AsyncMock()
            room.players[f"player-{i}"] = PlayerInfo(
                id=f"player-{i}",
                name=f"Player {i}",
                websocket=ws,
            )
        room.host_id = "player-0"
        room_manager.rooms[room_id] = room

        response = test_client.get("/api/rooms/random")
        assert response.status_code == 404

    def test_mid_game_room_not_returned(self, test_client):
        """Test that rooms mid-game are not returned"""
        room_id = "GAMING_ROOM"

        with test_client.websocket_connect(f"/party/{room_id}") as ws1:
            ws1.receive_text()
            ws1.send_text(json.dumps({"type": "join", "playerId": "player1", "name": "Player 1"}))
            ws1.receive_text()

            with test_client.websocket_connect(f"/party/{room_id}") as ws2:
                ws2.receive_text()
                ws2.send_text(json.dumps({"type": "join", "playerId": "player2", "name": "Player 2"}))
                ws1.receive_text()
                ws2.receive_text()

                ws1.send_text(
                    json.dumps({"type": "start_game", "difficulty": "medium", "rounds": 3, "roundLength": 60})
                )
                ws1.receive_text()  # start_game broadcast
                ws2.receive_text()

                response = test_client.get("/api/rooms/random")

                if response.status_code == 200:
                    data = response.json()
                    assert data["room_code"] != room_id


class TestPrivacyToggle:
    """Test suite for room privacy toggle"""

    def test_host_can_set_privacy(self, test_client):
        """Test that host can change room privacy"""
        room_id = "PRIVACY_TEST"

        with test_client.websocket_connect(f"/party/{room_id}") as ws:
            ws.receive_text()

            ws.send_text(json.dumps({"type": "join", "playerId": "host1", "name": "Host"}))
            ws.receive_text()

            # Initially public
            response = test_client.get("/api/rooms/random")
            assert response.status_code == 200
            assert response.json()["room_code"] == room_id

            # Host sets to private
            ws.send_text(json.dumps({"type": "privacy_changed", "isPrivate": True}))

            response = test_client.get("/api/rooms/random")
            assert response.status_code == 404

    def test_non_host_cannot_set_privacy(self, test_client):
        """Test that non-host players cannot change privacy"""
        from app.game_room import room_manager

        room_id = "NON_HOST_PRIVACY"

        with test_client.websocket_connect(f"/party/{room_id}") as ws:
            ws.receive_text()
            ws.send_text(json.dumps({"type": "join", "playerId": "host1", "name": "Host"}))
            ws.receive_text()

            with test_client.websocket_connect(f"/party/{room_id}") as ws2:
                ws2.receive_text()
                ws2.send_text(json.dumps({"type": "join", "playerId": "player2", "name": "Player 2"}))
                ws.receive_text()  # player_joined on ws1
                ws2.receive_text()  # player_joined on ws2

                # Non-host tries to set privacy (should be ignored)
                ws2.send_text(json.dumps({"type": "privacy_changed", "isPrivate": True}))

                room = room_manager.get_room(room_id)
                assert room is not None
                assert room.metadata.is_private is False
