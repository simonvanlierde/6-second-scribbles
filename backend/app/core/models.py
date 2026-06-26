"""Central registry to import domain model modules.

Importing this module ensures all declarative models are loaded
and `Base.metadata` is populated. Alembic and other tooling can
import `app.core.models` as a single entry point.
"""

# Import domain model modules here so they register with the Declarative `Base`.
from app.categories import models as categories_models
from app.users import models as users_models

__all__ = ["categories_models", "users_models"]
