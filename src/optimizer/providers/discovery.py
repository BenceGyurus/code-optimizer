from typing import Dict, List

from optimizer.providers.registry import registry


def discover_models() -> Dict[str, List[str]]:
    return {name: registry.get_provider(name).list_models() for name in registry.list_providers()}
