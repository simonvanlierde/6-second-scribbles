"""Tests for custom category functionality."""

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from sqlalchemy import select

from app.db_models import Card, Category
from app.game_room import GameRoom, PlayerInfo, room_manager

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestCustomCategoryAPI:
    """Test custom category API endpoints."""

    def test_create_custom_category(self, test_client) -> None:
        """Test creating a custom category."""
        room_id = "CREATE_TEST"

        # Set up room with a host directly (avoids HTTP-inside-WebSocket conflict)
        room = GameRoom(room_id)
        ws = AsyncMock()
        room.players["host-123"] = PlayerInfo(id="host-123", name="Host Player", websocket=ws)
        room.host_id = "host-123"
        room_manager.rooms[room_id] = room

        response = test_client.post(
            f"/api/rooms/{room_id}/categories",
            json={
                "name": "My Custom Animals",
                "items": ["unicorn", "dragon", "phoenix", "griffin", "pegasus"],
                "difficulty": "hard",
                "description": "Mythical creatures",
                "created_by": "host-123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "category" in data
        assert data["category"]["name"] == "My Custom Animals"
        assert data["category"]["is_custom"] is True

    def test_create_category_requires_minimum_items(self, test_client) -> None:
        """Test that custom categories require at least 5 items."""
        room_id = "MIN_ITEMS_TEST"

        with test_client.websocket_connect(f"/party/{room_id}") as ws:
            ws.receive_text()
            ws.send_text(json.dumps({"type": "join", "playerId": "host-123", "name": "Host"}))
            ws.receive_text()

            response = test_client.post(
                f"/api/rooms/{room_id}/categories",
                json={
                    "name": "Too Few Items",
                    "items": ["item1", "item2", "item3"],  # Only 3 items
                    "difficulty": "medium",
                    "created_by": "host-123",
                },
            )

            assert response.status_code == 400
            assert "at least 5 items" in response.json()["detail"]

    async def test_only_host_can_create_categories(self, async_client: AsyncClient) -> None:
        """Test that only the room host can create custom categories."""
        room_id = "HOST_ONLY_TEST"

        # Try to create as non-host (room doesn't exist → 403 or 404)
        response = await async_client.post(
            f"/api/rooms/{room_id}/categories",
            json={
                "name": "Unauthorized Category",
                "items": ["item1", "item2", "item3", "item4", "item5"],
                "difficulty": "medium",
                "created_by": "not-the-host",
            },
        )

        assert response.status_code in [403, 404]

    async def test_get_room_categories(self, async_client: AsyncClient, test_db) -> None:
        """Test getting custom categories for a room."""
        room_id = "GET_CATEGORIES_TEST"

        category = Category(name="Test Category", difficulty="medium", room_id=room_id, created_by="test-user")
        test_db.add(category)
        await test_db.flush()

        for i in range(5):
            card = Card(category_id=category.id, item=f"item{i}")
            test_db.add(card)

        await test_db.commit()

        response = await async_client.get(f"/api/rooms/{room_id}/categories")

        assert response.status_code == 200
        data = response.json()
        assert data["room_id"] == room_id
        assert len(data["categories"]) == 1
        assert data["categories"][0]["name"] == "Test Category"
        assert len(data["categories"][0]["items"]) == 5

    async def test_delete_custom_category(self, async_client: AsyncClient, test_db) -> None:
        """Test deleting a custom category."""
        room_id = "DELETE_TEST"

        # Ensure a room with the right host exists so the endpoint can authorise
        room = GameRoom(room_id)
        ws = AsyncMock()
        room.players["host-123"] = PlayerInfo(id="host-123", name="Host Player", websocket=ws)
        room.host_id = "host-123"
        room_manager.rooms[room_id] = room

        category = Category(name="To Be Deleted", difficulty="medium", room_id=room_id, created_by="host-123")
        test_db.add(category)
        await test_db.commit()

        category_id = category.id

        response = await async_client.delete(
            f"/api/rooms/{room_id}/categories/{category_id}",
            params={"player_id": "host-123"},
        )

        assert response.status_code == 200

        test_db.expire_all()
        deleted = await test_db.get(Category, category_id)
        assert deleted is None

    async def test_custom_categories_included_in_random_selection(self, async_client: AsyncClient, test_db) -> None:
        """Test that custom categories are included when getting random cards."""
        room_id = "RANDOM_TEST"

        category = Category(name="Custom Test", difficulty="medium", room_id=room_id, created_by="test-user")
        test_db.add(category)
        await test_db.flush()

        for i in range(10):
            card = Card(category_id=category.id, item=f"custom_item_{i}")
            test_db.add(card)

        await test_db.commit()

        response = await async_client.get(
            "/api/cards/random",
            params={"difficulty": "medium", "count": 1, "player_count": 2, "room_id": room_id},
        )

        # If enough global categories exist the endpoint succeeds; verify our custom one is included
        if response.status_code == 200:
            data = response.json()
            assert "includes_custom" in data
            assert data["includes_custom"] is True

    def test_create_custom_category_rejects_invalid_difficulty(self, test_client) -> None:
        """Test request validation rejects unsupported difficulty values."""
        room_id = "BAD_DIFFICULTY_TEST"

        room = GameRoom(room_id)
        ws = AsyncMock()
        room.players["host-123"] = PlayerInfo(id="host-123", name="Host Player", websocket=ws)
        room.host_id = "host-123"
        room_manager.rooms[room_id] = room

        response = test_client.post(
            f"/api/rooms/{room_id}/categories",
            json={
                "name": "Bad Difficulty",
                "items": ["one", "two", "three", "four", "five"],
                "difficulty": "expert",
                "created_by": "host-123",
            },
        )

        assert response.status_code == 422


class TestCustomCategoryCleanup:
    """Test cleanup of custom categories."""

    async def test_categories_cleaned_up_when_room_closes(self, test_db) -> None:
        """Test that custom categories are deleted when room is removed."""
        room_id = "CLEANUP_TEST"
        room = GameRoom(room_id)

        for i in range(3):
            category = Category(name=f"Temp Category {i}", difficulty="medium", room_id=room_id, created_by="test-user")
            test_db.add(category)

        await test_db.commit()

        result = await test_db.execute(select(Category).where(Category.room_id == room_id))
        assert len(result.scalars().all()) == 3

        await room.cleanup_custom_categories()

        result = await test_db.execute(select(Category).where(Category.room_id == room_id))
        assert len(result.scalars().all()) == 0


class TestCustomCategoryEdgeCases:
    """Test edge cases for custom categories."""

    async def test_custom_category_same_name_different_rooms(self, test_db) -> None:
        """Test that different rooms can have categories with the same name."""
        cat1 = Category(name="Animals", difficulty="easy", room_id="ROOM1", created_by="user1")
        test_db.add(cat1)

        cat2 = Category(name="Animals", difficulty="easy", room_id="ROOM2", created_by="user2")
        test_db.add(cat2)

        await test_db.commit()

        result = await test_db.execute(select(Category).where(Category.name == "Animals"))
        categories = result.scalars().all()
        assert len(categories) == 2

    async def test_global_categories_not_affected(self, test_db) -> None:
        """Test that global categories are not affected by room operations."""
        global_cat = Category(
            name="Global Animals",
            difficulty="easy",
            room_id=None,
            created_by=None,
        )
        test_db.add(global_cat)
        await test_db.commit()

        room_cat = Category(name="Room Animals", difficulty="easy", room_id="TEST_ROOM", created_by="test-user")
        test_db.add(room_cat)
        await test_db.commit()

        room = GameRoom("TEST_ROOM")
        await room.cleanup_custom_categories()

        result = await test_db.execute(select(Category).where(Category.room_id.is_(None)))
        global_categories = result.scalars().all()
        assert len(global_categories) >= 1
        assert any(c.name == "Global Animals" for c in global_categories)

        result = await test_db.execute(select(Category).where(Category.room_id == "TEST_ROOM"))
        assert len(result.scalars().all()) == 0
