from typing import Dict, Any

# A simple in-memory session manager to replace the global `GAMES_DATA` dictionary in handlers.py.
# In a real production environment, this should be backed by Redis. To keep the project
# portfolio-ready without adding a Redis dependency, we encapsulate it here.

class InMemorySessionManager:
    def __init__(self):
        self._games: Dict[str, Dict[str, Any]] = {}

    def get_game(self, game_id: str) -> Dict[str, Any]:
        return self._games.get(game_id)

    def set_game(self, game_id: str, data: Dict[str, Any]) -> None:
        self._games[game_id] = data

    def delete_game(self, game_id: str) -> None:
        if game_id in self._games:
            del self._games[game_id]

    def create_game(self, game_id: str, p1_id: int, p1_gender: str, is_distance: bool) -> None:
        self._games[game_id] = {
            "p1": p1_id, 
            "p2": None,
            "p1_gender": p1_gender, 
            "p2_gender": None,
            "is_distance": is_distance,
            "rounds": [], 
            "current_round": 0, 
            "answers": {},
            "generation_failed": False,
            "error_notified": False,
            "finished_guessing": set(),
            "results": {}
        }

game_sessions = InMemorySessionManager()
