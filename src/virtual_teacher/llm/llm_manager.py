"""
LLM Manager for OpenAI models.
Supports model tiers and switching.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List
import logging
from crewai import LLM

logger = logging.getLogger(__name__)


class OpenAILLMManager:
    """Manages OpenAI models and tier switching."""
    
    def __init__(self, config_path: str = "config/llm_config.yaml"):
        self.config = self._load_config(config_path)
        self.current_models = {}
        self._require_api_key()
        self._initialize_models()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load LLM configuration"""
        logger.info(f"Loading LLM config from {config_path}")
        config_file = Path(config_path)
        if not config_file.exists():
            logger.info(f"LLM config file not found at {config_path}, creating default config")
            # Create default config if not exists
            default_config = {
                "llms": {
                    "start": {
                        "primary": "gpt-4o-mini",
                        "fallback": "gpt-4o",
                    },
                    "scale": {
                        "primary": "gpt-4o",
                        "fallback": "gpt-4.1",
                        "high_performance": "gpt-4.1",
                    },
                    "active": "start",
                },
                "openai": {
                    "api_key_env": "OPENAI_API_KEY",
                    "base_url": None,
                    "organization": None,
                    "project": None,
                    "timeout": 120,
                    "temperature": 0.2,
                    "max_retries": 2,
                },
            }
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                yaml.dump(default_config, f)
            return default_config
        
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _require_api_key(self) -> None:
        openai_config = self.config.get("openai", {})
        api_key_env = openai_config.get("api_key_env") or "OPENAI_API_KEY"
        if not os.getenv(api_key_env):
            raise ValueError(
                f"{api_key_env} is required. Set it in your environment or .env file."
            )

    def _initialize_models(self):
        """Initialize OpenAI models based on the active tier."""
        active_tier = self.config["llms"]["active"]
        models = self.config["llms"][active_tier]
        
        for role, model_name in models.items():
            try:
                self.current_models[role] = self._build_llm(model_name)
                logger.info(f"Initialized {role} model: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize {role} model {model_name}: {e}")

    def _build_llm(self, model_name: str) -> LLM:
        """Build an OpenAI-backed CrewAI LLM instance."""
        openai_config = self.config.get("openai", {})
        api_key_env = openai_config.get("api_key_env") or "OPENAI_API_KEY"
        api_key = os.getenv(api_key_env)

        llm_kwargs: Dict[str, Any] = {}
        for key in (
            "timeout",
            "temperature",
            "base_url",
            "organization",
            "project",
            "max_retries",
            "max_tokens",
            "max_completion_tokens",
            "reasoning_effort",
        ):
            value = openai_config.get(key)
            if value is not None:
                llm_kwargs[key] = value

        if api_key:
            llm_kwargs["api_key"] = api_key

        return LLM(model=model_name, **llm_kwargs)

    def get_llm(self, role: str = "primary") -> LLM:
        """Get LLM instance for specified role"""
        if role in self.current_models:
            logger.debug(f"Returning LLM for role={role}")
            return self.current_models[role]
        else:
            logger.debug(f"Role {role} not found, falling back to primary")
            return self.current_models.get("primary")
    
    def switch_tier(self, new_tier: str):
        """Switch between start/scale tiers"""
        if new_tier in self.config['llms']:
            old_tier = self.config['llms']['active']
            self.config['llms']['active'] = new_tier
            self._initialize_models()
            logger.info(f"Switched tier from {old_tier} to {new_tier}")
        else:
            logger.error(f"Unknown tier: {new_tier}")
    
    def get_available_models(self) -> List[str]:
        """Get list of configured models across tiers."""
        models: List[str] = []
        for tier_name, tier_models in self.config.get("llms", {}).items():
            if tier_name == "active" or not isinstance(tier_models, dict):
                continue
            for model_name in tier_models.values():
                if isinstance(model_name, str):
                    models.append(model_name)
        return sorted(set(models))


# Global LLM manager instance
_llm_manager = None

def get_llm_manager() -> OpenAILLMManager:
    """Get global LLM manager instance"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = OpenAILLMManager()
    return _llm_manager
