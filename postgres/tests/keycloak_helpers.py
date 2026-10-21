import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "infra" / "keycloak"))

from provision import KeycloakLocal, local_origin

__all__ = ["KeycloakLocal", "local_origin"]
