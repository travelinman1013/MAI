from typing import Dict, Type
from src.core.agents.base import BaseAgentFramework

class AgentRegistry:
    _instance = None
    _agents: Dict[str, Type[BaseAgentFramework]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentRegistry, cls).__new__(cls)
        return cls._instance

    def register_agent(self, agent_class: Type[BaseAgentFramework]):
        if not issubclass(agent_class, BaseAgentFramework):
            raise ValueError(f"Class {agent_class.__name__} must inherit from BaseAgentFramework.")
        
        agent_name = agent_class.name # Assuming agent_class has a 'name' attribute
        if not agent_name:
            raise ValueError(f"Agent class {agent_class.__name__} must define a 'name' attribute.")
        
        if agent_name in self._agents:
            raise ValueError(f"Agent with name '{agent_name}' already registered.")
        
        self._agents[agent_name] = agent_class
        # print(f"Registered agent: {agent_name}") # Debug print

    def get_agent(self, agent_name: str) -> Type[BaseAgentFramework]:
        if agent_name not in self._agents:
            raise ValueError(f"Agent '{agent_name}' not found in registry.")
        return self._agents[agent_name]
    
    def list_agents(self) -> Dict[str, Type[BaseAgentFramework]]:
        return self._agents

    def _clear(self):
        """Clears all registered agents. Use only for testing."""
        self._agents.clear()

agent_registry = AgentRegistry()