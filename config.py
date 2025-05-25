import os

# API Configuration
API_URL = "https://api.anthropic.com/v1/complete"

# File Storage
TEMP_RESPONSE_FILE = "derniere_reponse_claude.txt"

# Model Configuration
MODELS = {
    "claude-3-opus-20240229": {
        "description": "Most powerful model, best for complex tasks, deep analysis, and nuanced content generation",
        "price_tier": "Highest"
    },
    "claude-3-sonnet-20240229": {
        "description": "Balanced model offering strong performance across a wide range of tasks",
        "price_tier": "Medium"
    },
    "claude-3-haiku-20240307": {
        "description": "Fastest model, optimized for quick responses and simpler tasks",
        "price_tier": "Lowest"
    },
    "claude-3-5-sonnet-20240620": {
        "description": "Improved version of Sonnet with better performance",
        "price_tier": "Medium-High"
    },
    "claude-3-5-haiku-20240307": {
        "description": "Fast model with improved capabilities over Claude 3 Haiku",
        "price_tier": "Low-Medium"
    },
    "claude-3-7-sonnet-20250219": {
        "description": "Latest Sonnet model with enhanced reasoning capabilities",
        "price_tier": "Medium-High"
    }
}
MODEL_NAME = "claude-3-7-sonnet-20250219"
MAX_TOKENS = 4000