"""
LLM Manager for handling multiple local models via Ollama
Supports Indian language processing and model switching
"""

import yaml
import ollama
from pathlib import Path
from typing import Dict, Any, Optional, List
from langchain_ollama import OllamaLLM
import logging
from crewai import LLM

logger = logging.getLogger(__name__)


class OllamaLLMManager:
    """Manages Ollama models and Indian language processing"""
    
    def __init__(self, config_path: str = "config/llm_config.yaml"):
        self.config = self._load_config(config_path)
        # self.client = ollama.Client(base_url=self.config['ollama']['base_url'])
        self.client = ollama.Client()
        self.current_models = {}
        self._initialize_models()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load LLM configuration"""
        config_file = Path(config_path)
        if not config_file.exists():
            # Create default config if not exists
            default_config = {
                'llms': {
                    'start': {
                        'primary': 'ollama/llama3.1:8b',
                        'fallback': 'ollama/qwen2.5:7b-instruct'
                    },
                    'scale': {
                        'primary': 'mixtral:8x7b-instruct', 
                        'fallback': 'llama3.1:70b-instruct',
                        'high_performance': 'qwen2.5:32b-instruct'
                    },
                    'active': 'start'
                },
                'ollama': {
                    'base_url': 'http://localhost:11434',
                    'timeout': 120
                }
            }
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                yaml.dump(default_config, f)
            return default_config
        
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _initialize_models(self):
        """Initialize and pull required models"""
        active_tier = self.config['llms']['active']
        models = self.config['llms'][active_tier]
        
        for role, model_name in models.items():
            try:
                # Check if model exists, pull if needed
                # self._ensure_model_available(model_name)
                self.current_models[role] = LLM(
                    model = model_name,
                    base_url = self.config['ollama']['base_url']
                )

                # OllamaLLM(
                #     model=model_name
                # )
                logger.info(f"Initialized {role} model: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize {role} model {model_name}: {e}")
    
    def _ensure_model_available(self, model_name: str):
        """Ensure model is available locally, pull if needed"""
        try:
            # Check if model exists
            models = self.client.list()
            available_models = [m['name'] for m in models['models']]
            
            if model_name not in available_models:
                logger.info(f"Pulling model {model_name}...")
                self.client.pull(model_name)
                logger.info(f"Successfully pulled {model_name}")
        except Exception as e:
            logger.error(f"Error ensuring model {model_name} is available: {e}")
            raise
    
    def get_llm(self, role: str = "primary") -> OllamaLLM:
        """Get LLM instance for specified role"""
        if role in self.current_models:
            return self.current_models[role]
        else:
            # Fallback to primary if role not found
            return self.current_models.get("primary")
    
    def switch_tier(self, new_tier: str):
        """Switch between start/scale tiers"""
        if new_tier in self.config['llms']:
            self.config['llms']['active'] = new_tier
            self._initialize_models()
            logger.info(f"Switched to {new_tier} tier")
        else:
            logger.error(f"Unknown tier: {new_tier}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available local models"""
        try:
            models = self.client.list()
            return [m['name'] for m in models['models']]
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []


# Global LLM manager instance
_llm_manager = None

def get_llm_manager() -> OllamaLLMManager:
    """Get global LLM manager instance"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = OllamaLLMManager()
    return _llm_manager
