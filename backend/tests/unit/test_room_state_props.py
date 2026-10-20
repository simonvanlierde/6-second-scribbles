"""Property tests: random sequences of room-metadata writes keep the room consistent."""

from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule

from app.rooms.player_lifecycle import ABSENT_BINDING_GRACE_SECONDS, MAX_ABSENT_BINDINGS
from app.rooms.state import GuessSubmissionState, PlayerPromptAssignmentState, RoomMetadataState, RoomState

PLAYER_COUNT = 10
player_ids = st.integers(min_value=0, max_value=PLAYER_COUNT - 1).map(lambda n: f"p{n}")
CARD = PlayerPromptAssignmentState(category="Pets", items=["cat", "dog"])


class RoomMetadataMachine(RuleBasedStateMachine):
    """Drives `RoomMetadataState` the way `GameRoom` and `player_lifecycle` call it."""

    def __init__(self) -> None:
        super().__init__()
        self.metadata = RoomMetadataState()
        self.present: set[str] = set()
        self.next_crowd_id = 0
        self.now = 0.0
        # Bindings of departed players as they were when each left: (left at, key hash, user id).
        self.departed: dict[str, tuple[float, str | None, str | None]] = {}

    def _trim(self, keep: int = MAX_ABSENT_BINDINGS) -> None:
        self.metadata.trim_absent_identities(self.present, keep=keep, now=self.now, grace=ABSENT_BINDING_GRACE_SECONDS)

    def _admits(self, player_id: str) -> bool:
        # Mirrors the new-player check in player_lifecycle._check_identity.
        metadata = self.metadata
        if (
            player_id in self.present
            or player_id in metadata.player_rejoin_keys
            or player_id in metadata.player_user_ids
        ):
            return True
        if len(metadata.absent_identities(self.present)) >= MAX_ABSENT_BINDINGS:
            self._trim(keep=MAX_ABSENT_BINDINGS - 1)
        return len(metadata.absent_identities(self.present)) < MAX_ABSENT_BINDINGS

    def _leave(self, player_id: str, *, forget_identity: bool) -> None:
        # Mirrors player_lifecycle.remove_player.
        was_present = player_id in self.present
        self.present.discard(player_id)
        self.metadata.forget_player(player_id, forget_identity=forget_identity)
        if forget_identity:
            self.departed.pop(player_id, None)
            return
        # Removing a player who already left does not restart their grace period.
        key = self.metadata.player_rejoin_keys.get(player_id)
        user = self.metadata.player_user_ids.get(player_id)
        if was_present and (key is not None or user is not None):
            self.departed[player_id] = (self.now, key, user)
        self._trim()

    @rule(player_id=player_ids, guest=st.booleans(), with_key=st.booleans())
    def join(self, player_id: str, *, guest: bool, with_key: bool) -> None:
        """A player joins or reconnects, as a guest or with an account."""
        self._join(player_id, guest=guest, with_key=with_key)

    def _join(self, player_id: str, *, guest: bool, with_key: bool) -> bool:
        """Join if the room lets this player in, and report whether it did."""
        if not self._admits(player_id):
            return False
        self.present.add(player_id)
        self.departed.pop(player_id, None)
        self.metadata.seat_player(
            player_id,
            locale="en",
            user_id=None if guest else f"user-{player_id}",
            rejoin_key_hash=f"key-{player_id}" if with_key else None,
        )
        return True

    @rule(player_id=player_ids, forget_identity=st.booleans())
    def leave(self, player_id: str, *, forget_identity: bool) -> None:
        """A player drops, leaves or is kicked; a departed player keeps their score."""
        score = self.metadata.player_scores.get(player_id)
        self._leave(player_id, forget_identity=forget_identity)
        assert self.metadata.player_scores.get(player_id) == score, "a departed player keeps their score"

    @rule(count=st.integers(min_value=1, max_value=MAX_ABSENT_BINDINGS + 5))
    def crowd_passes_through(self, count: int) -> None:
        """Many one-off guests join and drop, enough to reach the binding cap in a few steps."""
        for _ in range(count):
            player_id = f"crowd{self.next_crowd_id}"
            self.next_crowd_id += 1
            if not self._join(player_id, guest=True, with_key=True):
                return
            self._leave(player_id, forget_identity=False)

    @rule(seconds=st.integers(min_value=1, max_value=2 * ABSENT_BINDING_GRACE_SECONDS))
    def time_passes(self, seconds: int) -> None:
        """The clock moves on, so earlier departures age past the grace period."""
        self.now += seconds

    @rule()
    def start_round(self) -> None:
        """A new round deals one card to each present player."""
        self.metadata.reset_round(cards=dict.fromkeys(sorted(self.present), CARD))

    @rule(player_id=player_ids)
    def mark_ready(self, player_id: str) -> None:
        """A player finishes drawing."""
        self.metadata.mark_ready(player_id)

    @precondition(lambda self: self.present)
    @rule()
    def start_guessing(self) -> None:
        """Each present player gets the next player's drawing to guess."""
        order = sorted(self.present)
        targets = {pid: order[(i + 1) % len(order)] for i, pid in enumerate(order) if len(order) > 1}
        self.metadata.start_guessing(targets, started_at=1)

    @rule(player_id=player_ids, guesses=st.lists(st.text(max_size=8), max_size=3))
    def record_guess(self, player_id: str, guesses: list[str]) -> None:
        """A player with a target submits guesses once."""
        target = self.metadata.guess_targets.get(player_id)
        # The caller refuses a second submission and a guess without a target.
        if target is None or player_id in self.metadata.submitted_players:
            return
        self.metadata.record_guess(
            GuessSubmissionState(player_id=player_id, target_player_id=target, guesses=guesses),
        )

    @rule(points=st.dictionaries(player_ids, st.integers(min_value=0, max_value=30), max_size=4))
    def add_round_points(self, points: dict[str, int]) -> None:
        """Round points add to each player's running score."""
        before = dict(self.metadata.player_scores)
        self.metadata.add_round_points(points)
        for player_id, gained in points.items():
            assert self.metadata.player_scores[player_id] == before.get(player_id, 0) + gained

    @rule()
    def reset_game(self) -> None:
        """Back to the lobby: every present player starts on zero."""
        self.metadata.reset_game(self.present)
        assert self.metadata.player_scores == dict.fromkeys(self.present, 0)

    @invariant()
    def only_present_players_hold_a_card(self) -> None:
        """No departed player holds a card."""
        # A dict holds one card per key, so this also means at most one card each.
        assert set(self.metadata.player_assignments) <= self.present

    @invariant()
    def absent_identity_bindings_are_capped(self) -> None:
        """Departed players' bindings stay bounded: newcomers stop at the cap, then present players can still drop."""
        assert len(self.metadata.absent_identities(self.present)) <= MAX_ABSENT_BINDINGS + PLAYER_COUNT

    @invariant()
    def recent_departures_keep_their_binding(self) -> None:
        """No flood of joins and drops frees the seat of a player who left within the grace period."""
        for player_id, (left_at, key, user) in self.departed.items():
            if self.now - left_at < ABSENT_BINDING_GRACE_SECONDS:
                assert self.metadata.player_rejoin_keys.get(player_id) == key, player_id
                assert self.metadata.player_user_ids.get(player_id) == user, player_id

    @invariant()
    def present_players_keep_their_seat(self) -> None:
        """Each present player has exactly one distinct seat."""
        assert set(self.metadata.player_seats) == self.present
        assert len(set(self.metadata.player_seats.values())) == len(self.present)

    @invariant()
    def survives_redis_round_trip(self) -> None:
        """The room loads back from its JSON dump unchanged."""
        state = RoomState(room_id="room", metadata=self.metadata)
        restored = RoomState.model_validate_json(state.model_dump_json())
        assert restored == state
        # Trimming relies on insertion order, so the restore must keep it.
        assert list(restored.metadata.player_rejoin_keys) == list(self.metadata.player_rejoin_keys)
        assert list(restored.metadata.player_seats) == list(self.metadata.player_seats)


RoomMetadataMachine.TestCase.settings = settings(max_examples=60, stateful_step_count=25, deadline=None)
TestRoomMetadataMachine = RoomMetadataMachine.TestCase
