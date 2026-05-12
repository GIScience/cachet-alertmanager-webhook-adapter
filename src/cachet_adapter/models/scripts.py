from pydantic import RootModel

from cachet_adapter.models.cachet import BaseComponent

ComponentData = RootModel[dict[str, list[BaseComponent]]]
