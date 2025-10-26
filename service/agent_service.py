"""
Agent service for handling YAML file operations
"""
import os
import yaml
import re
from typing import List, Optional
from pathlib import Path

from model.agent import Agent, AgentCreate, AgentUpdate


class AgentService:
    """Service for managing agent YAML files"""
    
    AGENTS_DIR = Path(__file__).parent.parent / "agents"
    
    @classmethod
    def _get_yaml_path(cls, name: str) -> Path:
        """Get the YAML file path for an agent"""
        # First check for dangerous patterns before sanitization
        if not name or '..' in name or '/' in name or '\\' in name or name.startswith('.'):
            raise ValueError(f"Invalid agent name: {name}")
        
        # Sanitize the name for filename  
        safe_name = re.sub(r'[^\w\-_]', '-', name.lower()).strip('-')
        if not safe_name:
            raise ValueError(f"Invalid agent name: {name}")
            
        return cls.AGENTS_DIR / f"{safe_name}.yml"
    
    @classmethod
    def _ensure_agents_dir(cls):
        """Ensure the agents directory exists"""
        cls.AGENTS_DIR.mkdir(exist_ok=True)
    
    @classmethod
    async def get_all_agents(cls) -> List[Agent]:
        """Get all agents from YAML files"""
        cls._ensure_agents_dir()
        agents = []
        
        for yaml_file in cls.AGENTS_DIR.glob("*.yml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and isinstance(data, dict):
                        # Validate required fields exist before creating Agent
                        required_fields = ['name', 'description', 'role', 'provider', 'model', 'task']
                        if all(field in data for field in required_fields):
                            agent = Agent(**data)
                            agents.append(agent)
            except Exception as e:
                print(f"Error loading agent from {yaml_file}: {e}")
                continue
        
        return sorted(agents, key=lambda x: x.name)
    
    @classmethod
    async def get_agent_by_name(cls, name: str) -> Optional[Agent]:
        """Get a specific agent by name"""
        yaml_path = cls._get_yaml_path(name)
        
        if not yaml_path.exists():
            return None
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data and isinstance(data, dict):
                    # Validate required fields exist before creating Agent
                    required_fields = ['name', 'description', 'role', 'provider', 'model', 'task']
                    if all(field in data for field in required_fields):
                        return Agent(**data)
        except Exception as e:
            print(f"Error loading agent {name}: {e}")
        
        return None
    
    @classmethod
    async def create_agent(cls, agent_data: AgentCreate) -> Agent:
        """Create a new agent"""
        cls._ensure_agents_dir()
        
        # Check if agent already exists
        existing = await cls.get_agent_by_name(agent_data.name)
        if existing:
            raise ValueError(f"Agent with name '{agent_data.name}' already exists")
        
        agent = Agent(**agent_data.dict())
        yaml_path = cls._get_yaml_path(agent.name)
        
        # Write YAML file
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(agent.dict(), f, default_flow_style=False, allow_unicode=True, indent=2)
        
        return agent
    
    @classmethod
    async def update_agent(cls, name: str, agent_data: AgentUpdate) -> Optional[Agent]:
        """Update an existing agent"""
        existing = await cls.get_agent_by_name(name)
        if not existing:
            return None
        
        # Update fields
        update_dict = agent_data.dict(exclude_unset=True)
        updated_data = existing.dict()
        updated_data.update(update_dict)
        
        # If name changed, we need to rename the file
        old_yaml_path = cls._get_yaml_path(name)
        new_agent = Agent(**updated_data)
        new_yaml_path = cls._get_yaml_path(new_agent.name)
        
        # Write new file
        with open(new_yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(new_agent.dict(), f, default_flow_style=False, allow_unicode=True, indent=2)
        
        # Remove old file if name changed
        if old_yaml_path != new_yaml_path and old_yaml_path.exists():
            old_yaml_path.unlink()
        
        return new_agent
    
    @classmethod
    async def delete_agent(cls, name: str) -> bool:
        """Delete an agent"""
        yaml_path = cls._get_yaml_path(name)
        
        if yaml_path.exists():
            yaml_path.unlink()
            return True
        
        return False
    
    @classmethod
    async def agent_exists(cls, name: str) -> bool:
        """Check if an agent exists"""
        yaml_path = cls._get_yaml_path(name)
        return yaml_path.exists()
    
    @classmethod
    async def clone_agent(cls, name: str) -> Agent:
        """Clone an existing agent with '-clone' suffix"""
        # Get the original agent
        original_agent = await cls.get_agent_by_name(name)
        if not original_agent:
            raise ValueError(f"Agent with name '{name}' not found")
        
        # Extract base name by removing existing clone suffixes to prevent long names
        base_name = original_agent.name
        if '-clone' in base_name:
            # Remove existing clone suffixes (e.g., "agent-clone-1" -> "agent")
            parts = base_name.split('-clone')
            base_name = parts[0]
        
        # Generate unique clone name
        clone_name = f"{base_name}-clone"
        counter = 1
        while await cls.agent_exists(clone_name):
            clone_name = f"{base_name}-clone-{counter}"
            counter += 1
        
        # Create the cloned agent data
        agent_data = AgentCreate(
            name=clone_name,
            description=original_agent.description,
            role=original_agent.role,
            provider=original_agent.provider,
            model=original_agent.model,
            task=original_agent.task
        )
        
        # Create the cloned agent
        return await cls.create_agent(agent_data)