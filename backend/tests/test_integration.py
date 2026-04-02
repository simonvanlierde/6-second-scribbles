"""Integration tests for complete game flows"""

import json
from contextlib import ExitStack

import pytest


@pytest.mark.integration
class TestCompleteGameFlow:
    """Test complete game flow from start to finish"""

    def test_full_game_flow(self, test_client):
        """Test a complete game from lobby through scoring"""
        with test_client.websocket_connect("/party/GAME01") as ws1:
            state = json.loads(ws1.receive_text())
            assert state["type"] == "room_state"

            ws1.send_text(json.dumps({"type": "join", "playerId": "p1", "name": "Alice"}))
            player_joined = json.loads(ws1.receive_text())
            assert player_joined["type"] == "player_joined"
            assert len(player_joined["players"]) == 1

            with test_client.websocket_connect("/party/GAME01") as ws2:
                ws2.receive_text()  # Initial state

                ws2.send_text(json.dumps({"type": "join", "playerId": "p2", "name": "Bob"}))

                # Both receive player_joined
                msg1 = json.loads(ws1.receive_text())
                msg2 = json.loads(ws2.receive_text())
                assert msg1["type"] == "player_joined"
                assert msg2["type"] == "player_joined"
                assert len(msg1["players"]) == 2

                # Host starts game (1 round so the test stays fast)
                ws1.send_text(
                    json.dumps({"type": "start_game", "difficulty": "medium", "rounds": 1, "roundLength": 10}),
                )

                start1 = json.loads(ws1.receive_text())
                start2 = json.loads(ws2.receive_text())
                assert start1["type"] == "start_game"
                assert start2["type"] == "start_game"

                # Start first round with cards for each player
                ws1.send_text(
                    json.dumps(
                        {
                            "type": "start_round",
                            "round": 1,
                            "cards": {
                                "p1": {"category": "Animals", "items": ["cat", "dog"]},
                                "p2": {"category": "Foods", "items": ["pizza", "burger"]},
                            },
                        },
                    ),
                )

                round1 = json.loads(ws1.receive_text())
                round2 = json.loads(ws2.receive_text())
                assert round1["type"] == "start_round"
                assert round2["type"] == "start_round"
                assert "roundStartTime" in round1
                assert round1["roundStartTime"] > 0

                # Players draw
                ws1.send_text(
                    json.dumps(
                        {
                            "type": "draw_stroke",
                            "playerId": "p1",
                            "stroke": {"color": "#000", "width": 2, "points": [{"x": 10, "y": 20}]},
                        },
                    ),
                )

                draw1 = json.loads(ws1.receive_text())
                draw2 = json.loads(ws2.receive_text())
                assert draw1["type"] == "draw_stroke"
                assert draw2["type"] == "draw_stroke"

                # Host transitions to guessing phase (server starts scoring timeout)
                ws1.send_text(json.dumps({"type": "start_guessing"}))

                guessing1 = json.loads(ws1.receive_text())
                guessing2 = json.loads(ws2.receive_text())
                assert guessing1["type"] == "start_guessing"
                assert guessing2["type"] == "start_guessing"

                # Both players submit guesses; after both submit, server scores and
                # broadcasts round_complete to everyone
                ws1.send_text(
                    json.dumps(
                        {
                            "type": "submit_guess",
                            "playerId": "p1",
                            "targetPlayerId": "p2",
                            "guesses": ["pizza", "burger"],
                        },
                    ),
                )
                ws2.send_text(
                    json.dumps(
                        {
                            "type": "submit_guess",
                            "playerId": "p2",
                            "targetPlayerId": "p1",
                            "guesses": ["cat", "dog"],
                        },
                    ),
                )

                # Server broadcasts round_complete once both guesses are in
                complete1 = json.loads(ws1.receive_text())
                complete2 = json.loads(ws2.receive_text())
                assert complete1["type"] == "round_complete"
                assert complete2["type"] == "round_complete"
                assert "scores" in complete1
                assert "results" in complete1

    def test_waiting_room_drawing(self, test_client):
        """Test collaborative drawing in waiting room"""
        with test_client.websocket_connect("/party/DRAW01") as ws1:
            ws1.receive_text()  # Initial state

            # Player 1 joins and becomes host
            ws1.send_text(json.dumps({"type": "join", "playerId": "p1", "name": "Alice"}))
            ws1.receive_text()  # player_joined

            with test_client.websocket_connect("/party/DRAW01") as ws2:
                ws2.receive_text()  # Initial state

                # Player 2 joins
                ws2.send_text(json.dumps({"type": "join", "playerId": "p2", "name": "Bob"}))
                ws1.receive_text()  # player_joined
                ws2.receive_text()  # player_joined

                # Player 1 draws
                ws1.send_text(
                    json.dumps(
                        {
                            "type": "draw_stroke",
                            "playerId": "p1",
                            "stroke": {
                                "color": "#FF0000",
                                "width": 3,
                                "points": [{"x": 50, "y": 50}, {"x": 100, "y": 100}],
                            },
                        },
                    ),
                )

                # Both players see the stroke
                stroke1 = json.loads(ws1.receive_text())
                stroke2 = json.loads(ws2.receive_text())
                assert stroke1["type"] == "draw_stroke"
                assert stroke2["type"] == "draw_stroke"

                # Host clears pad
                ws1.send_text(json.dumps({"type": "drawpad_clear", "playerId": "p1"}))

                # Both receive clear
                clear1 = json.loads(ws1.receive_text())
                clear2 = json.loads(ws2.receive_text())
                assert clear1["type"] == "drawpad_clear"
                assert clear2["type"] == "drawpad_clear"

    def test_settings_sync(self, test_client):
        """Test that settings are synced across all players"""
        with test_client.websocket_connect("/party/SETTINGS01") as ws1:
            ws1.receive_text()  # Initial state

            # Host joins
            ws1.send_text(json.dumps({"type": "join", "playerId": "host", "name": "Host"}))
            ws1.receive_text()  # player_joined

            with test_client.websocket_connect("/party/SETTINGS01") as ws2:
                ws2.receive_text()  # Initial state

                # Player joins
                ws2.send_text(json.dumps({"type": "join", "playerId": "player", "name": "Player"}))
                ws1.receive_text()  # player_joined
                ws2.receive_text()  # player_joined

                # Host updates settings
                ws1.send_text(
                    json.dumps({"type": "settings_update", "difficulty": "hard", "rounds": 10, "roundLength": 45}),
                )

                # Both receive settings update
                settings1 = json.loads(ws1.receive_text())
                settings2 = json.loads(ws2.receive_text())

                assert settings1["type"] == "settings_update"
                assert settings2["type"] == "settings_update"
                assert settings1["difficulty"] == "hard"
                assert settings1["rounds"] == 10

                # Non-host tries to update (should be ignored)
                ws2.send_text(
                    json.dumps({"type": "settings_update", "difficulty": "easy", "rounds": 3, "roundLength": 30}),
                )

                # Should not receive any update (timeout if we wait)

    def test_reconnection_scenario(self, test_client):
        """Test player rejoining after disconnect"""
        room_id = "RECONNECT01"

        # Player 1 joins
        with test_client.websocket_connect(f"/party/{room_id}") as ws1:
            ws1.receive_text()  # Initial state

            ws1.send_text(json.dumps({"type": "join", "playerId": "p1", "name": "Alice"}))
            ws1.receive_text()  # player_joined

        # Player 1 disconnected, now reconnects
        with test_client.websocket_connect(f"/party/{room_id}") as ws1_new:
            state = json.loads(ws1_new.receive_text())
            assert state["type"] == "room_state"

            # Room should be empty now (previous connection cleaned up)
            # Player rejoins with same ID
            ws1_new.send_text(json.dumps({"type": "join", "playerId": "p1", "name": "Alice"}))

            joined = json.loads(ws1_new.receive_text())
            assert joined["type"] == "player_joined"


@pytest.mark.integration
class TestMultiRoomScenarios:
    """Test scenarios with multiple rooms"""

    def test_concurrent_games(self, test_client):
        """Test multiple games running concurrently"""
        with ExitStack() as stack:
            rooms = []
            for i in range(3):
                room_id = f"CONCURRENT0{i + 1}"

                ws1 = stack.enter_context(test_client.websocket_connect(f"/party/{room_id}"))
                ws1.receive_text()
                ws1.send_text(json.dumps({"type": "join", "playerId": f"p{i}-1", "name": f"Player {i}-1"}))
                ws1.receive_text()

                ws2 = stack.enter_context(test_client.websocket_connect(f"/party/{room_id}"))
                ws2.receive_text()
                ws2.send_text(json.dumps({"type": "join", "playerId": f"p{i}-2", "name": f"Player {i}-2"}))
                ws1.receive_text()
                ws2.receive_text()

                rooms.append((ws1, ws2))

            # All games should work independently
            for ws1, ws2 in rooms:
                ws1.send_text(
                    json.dumps({"type": "start_game", "difficulty": "medium", "rounds": 3, "roundLength": 60})
                )
                msg1 = json.loads(ws1.receive_text())
                msg2 = json.loads(ws2.receive_text())

                assert msg1["type"] == "start_game"
                assert msg2["type"] == "start_game"


def _drain(connections: list, count: int = 1) -> None:
    """Drain `count` pending messages from each connection in the list."""
    for conn in connections:
        for _ in range(count):
            conn.receive_text()


@pytest.mark.integration
@pytest.mark.slow
class TestLoadScenarios:
    """Test scenarios with many players"""

    def test_max_players_in_room(self, test_client):
        """Test room with maximum players (10)"""
        room_id = "MAX_PLAYERS"

        with ExitStack() as stack:
            connections = []

            # Add 10 players, draining all pending messages after each join so
            # no connection has a stale queue that would cause later reads to hang.
            for i in range(10):
                ws = stack.enter_context(test_client.websocket_connect(f"/party/{room_id}"))
                ws.receive_text()  # Initial room_state

                ws.send_text(json.dumps({"type": "join", "playerId": f"player-{i}", "name": f"Player {i}"}))

                # The server broadcasts player_joined to ALL current connections.
                ws.receive_text()  # player_joined on new connection
                _drain(connections)  # drain each existing connection

                connections.append(ws)

            # Verify all players can receive a broadcast from the host
            host_ws = connections[0]
            host_ws.send_text(
                json.dumps({"type": "settings_update", "difficulty": "hard", "rounds": 5, "roundLength": 45}),
            )

            for ws in connections:
                msg = json.loads(ws.receive_text())
                assert msg["type"] == "settings_update"
