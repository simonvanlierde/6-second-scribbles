---
# spell-checker: ignore elefant, htmlcov
---
# FastAPI Backend

## Overview

Modern, scalable backend for Six Second Scribbles using:

- **FastAPI** - High-performance async web framework
- **PostgreSQL** - Reliable database for game data
- **SQLAlchemy** - Async ORM for database operations
- **RapidFuzz** - Fast fuzzy string matching for guess scoring
- **WebSockets** - Real-time multiplayer communication

## Features

- ✅ PostgreSQL database for card/category storage
- ✅ Fuzzy matching for guess validation (handles typos, plurals)
- ✅ REST API for categories and cards
- ✅ **Custom categories per room** - hosts can create room-specific categories
- ✅ WebSocket support for real-time gameplay
- ✅ Comprehensive test suite (90%+ coverage)
- ✅ Database migrations with Alembic
- ✅ Docker Compose for local development

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

### 2. Setup Database

Using Docker (recommended):

```bash
make db-setup  # Starts PostgreSQL, runs migrations, seeds data
```

Manual setup:

```bash
# Start PostgreSQL (via Docker or local install)
docker-compose up -d

# Run migrations
alembic upgrade head

# Seed database with card data
python seed_data.py
```

### 3. Run Development Server

```bash
make dev
# Or: uvicorn main:app --reload --port 8000
```

Visit:

- API: <http://localhost:8000>
- Interactive Docs: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

## Database Management

```bash
make db-up      # Start PostgreSQL container
make db-down    # Stop PostgreSQL container
make db-migrate # Run pending migrations
make db-seed    # Seed database with card data
make db-reset   # Clear and reseed database
make db-setup   # Complete setup (up + migrate + seed)
```

## API Endpoints

### Health Check

```bash
GET /  # API status
```

### Categories

```bash
GET /api/categories                # List all categories
GET /api/categories?difficulty=easy  # Filter by difficulty
GET /api/categories/{id}           # Get category with items
```

### Cards

```bash
GET /api/cards/random?difficulty=medium&count=5&player_count=4
# Get random cards for a game
```

### Scoring

```bash
POST /api/score/guesses
# Score player guesses with fuzzy matching
Body: {
  "guesses": ["cat", "elefant", "zebra"],
  "correct_answers": ["cat", "elephant", "zebra"],
  "alternatives": {}
}
```

### Custom Categories (Room-Specific)

```bash
POST /api/rooms/{room_id}/categories
# Create a custom category for a room (host only)
Body: {
  "name": "My Custom Category",
  "items": ["item1", "item2", ... "item10"],  # Min 5 items
  "difficulty": "medium",
  "created_by": "player-id"
}

GET /api/rooms/{room_id}/categories
# List all custom categories for a room

DELETE /api/rooms/{room_id}/categories/{category_id}?player_id=host-id
# Delete a custom category (host only)
```

**Features:**

- Only the room host can create/delete custom categories
- Minimum 5 items required per category
- Custom categories are automatically included in card selection for that room
- Automatically cleaned up when room closes
- Different rooms can have categories with the same name
- WebSocket broadcasts notify all players when categories are added/removed

### Rooms

```bash
GET /rooms/{room_id}/status  # Get room status
WS /party/{room_id}          # WebSocket for real-time gameplay
```

## Testing

Comprehensive test suite with 90%+ coverage.

### Installation

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

## Running Tests

### Run all tests

```bash
pytest
```

### Run with coverage report

```bash
pytest --cov=. --cov-report=html
```

Then open `htmlcov/index.html` in your browser to see the detailed coverage report.

### Run specific test files

```bash
# Test game room logic only
pytest tests/test_game_room.py

# Test WebSocket endpoints only
pytest tests/test_main.py

# Test integration scenarios
pytest tests/test_integration.py
```

### Run by marker

```bash
# Run integration tests only
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Verbose output

```bash
pytest -v
```

### Stop on first failure

```bash
pytest -x
```

### Run specific test

```bash
pytest tests/test_game_room.py::TestGameRoom::test_add_first_player_becomes_host
```

## Test Organization

```bash
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── test_game_room.py        # Game room management tests
├── test_main.py             # API endpoint and WebSocket tests
└── test_integration.py      # End-to-end integration tests
```

### Test Files

- **conftest.py**: Shared fixtures including mock WebSockets, test clients, sample messages
- **test_game_room.py**: Unit tests for `GameRoom` and `RoomManager` classes
  - Player management
  - Host transfer logic
  - Idle player detection
  - Broadcasting and messaging
- **test_main.py**: FastAPI endpoint and WebSocket connection tests
  - HTTP endpoints
  - WebSocket connection lifecycle
  - Message handling
  - Error handling
- **test_integration.py**: Full game flow integration tests
  - Complete game scenarios
  - Multi-room scenarios
  - Concurrent games
  - High player count tests

## Test Markers

Tests are marked with the following markers:

- `@pytest.mark.asyncio`: Async test (auto-detected)
- `@pytest.mark.integration`: Integration test
- `@pytest.mark.slow`: Slow-running test (e.g., idle timeout tests)

## Coverage Goals

We aim for:

- **Overall coverage**: >90%
- **Critical paths** (game room, message handling): 100%
- **Integration scenarios**: All major flows covered

Current coverage can be viewed by running `pytest --cov`.

## Writing New Tests

### Example Unit Test

```python
async def test_my_feature(game_room, mock_websocket):
    """Test description"""
    # Arrange
    await game_room.add_player("p1", "Alice", mock_websocket)

    # Act
    result = await game_room.some_method()

    # Assert
    assert result == expected_value
```

### Example Integration Test

```python
@pytest.mark.integration
def test_complete_flow(test_client):
    """Test complete game flow"""
    with test_client.websocket_connect("/party/TEST") as ws:
        ws.receive_text()  # Initial state

        # Send messages and verify responses
        ws.send_text(json.dumps({"type": "join", ...}))
        response = json.loads(ws.receive_text())

        assert response["type"] == "player_joined"
```

## Continuous Integration

Tests are configured to run automatically in CI via GitHub Actions (see `.github/workflows/test.yml`).

### Local CI Simulation

Run the full test suite as it would run in CI:

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run linter
ruff check .

# Run type checker
mypy .

# Run tests with coverage
pytest --cov=. --cov-report=term-missing

# Format check
black --check .
```

## Debugging Tests

### Print debugging

```bash
pytest -s  # Don't capture stdout
```

### PDB debugging

```python
def test_something():
    import pdb; pdb.set_trace()  # Breakpoint
    # ... test code
```

### Pytest debugging

```bash
pytest --pdb  # Drop into debugger on failure
```

## Fixtures

Common fixtures available in all tests (defined in `conftest.py`):

- `test_client`: Synchronous FastAPI test client
- `async_client`: Async HTTP client
- `mock_websocket`: Mock WebSocket connection
- `game_room`: Fresh GameRoom instance
- `room_with_players`: GameRoom with 2 players
- `room_manager`: RoomManager instance
- `sample_messages`: Dictionary of sample game messages

## Best Practices

1. **Use descriptive test names**: `test_player_becomes_host_when_first_to_join`
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **One assertion concept per test**: Test one thing at a time
4. **Use fixtures**: Reuse common setup code
5. **Mock external dependencies**: Use AsyncMock for WebSockets
6. **Test edge cases**: Empty rooms, invalid input, disconnections
7. **Test error handling**: What happens when things go wrong?

## Performance Testing

For load testing the WebSocket server:

```bash
# Install locust
pip install locust

# Run load tests (if implemented)
locust -f tests/load_test.py
```

## Troubleshooting

### Tests hanging

- Check for missing `await` keywords in async tests
- Verify WebSocket connections are properly closed
- Check for infinite loops in idle check tasks

### Import errors

- Ensure you're in the backend directory
- Check that `PYTHONPATH` includes the backend directory
- Verify all dependencies are installed

### Flaky tests

- Use `pytest-repeat` to run flaky tests multiple times
- Check for race conditions in async code
- Ensure proper cleanup in fixtures

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)
