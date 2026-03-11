from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from loguru import logger


def get_model_settings(model_name: str, router_path: Path | None = None) -> dict:
    """Get optimized settings for a given model name from router.yaml"""
    if router_path is None:
        router_path = (
            Path(__file__).parent.parent / '.cursor' / 'config' / 'router.yaml'
        )
    with open(router_path) as f:
        router_data = yaml.safe_load(f)

    # Find the model in model_list
    for model in router_data.get('model_list', []):
        if model['model_name'] == model_name:
            return model.get('litellm_params', {})

    raise ValueError(f'Model {model_name} not found in router.yaml')


def count_tokens(text: str) -> int:
    """Count tokens using a simple whitespace-based approach.
    For more accurate counting, consider integrating a proper tokenizer."""
    words = re.findall(r'\S+', text)
    return len(words)


class ContextMonitor:
    def __init__(self):
        self.context_stats = {
            'total_attempts': 0,
            'successful_attempts': 0,
            'context_overflows': 0,
            'model_usage': {},
        }
        self.config = {
            'warning_threshold': 70,  # %
            'fallback_threshold': 80,  # %
        }

    def track_usage(self, model_name: str, prompt_length: int, max_window: int) -> bool:
        """Track context window usage and return if it's within thresholds"""
        self.context_stats['total_attempts'] += 1
        usage_percentage = (prompt_length / max_window) * 100

        # Update model-specific stats
        model_data = self.context_stats['model_usage'].get(
            model_name,
            {
                'attempts': 0,
                'overflows': 0,
                'total_prompt_tokens': 0,
                'max_window_used': max_window,
            },
        )
        model_data['attempts'] += 1
        model_data['total_prompt_tokens'] += prompt_length

        # Check thresholds
        if usage_percentage > self.config['warning_threshold']:
            pct = f'{usage_percentage:.1f}%'
            logger.warning(f'[context] high context usage: {pct} for {model_name}')
            if usage_percentage > self.config['fallback_threshold']:
                model_data['overflows'] += 1
                self.context_stats['context_overflows'] += 1
                return False

        # Update stats
        self.context_stats['model_usage'][model_name] = model_data
        if not model_data.get('overflows', 0):
            self.context_stats['successful_attempts'] += 1
        return True

    def get_model_stats(self, model_name: str) -> dict[str, Any]:
        """Get statistics for a specific model"""
        model_data = self.context_stats['model_usage'].get(model_name, {})
        if not model_data:
            return {}

        avg_usage = (
            (model_data['total_prompt_tokens'] / model_data['attempts'])
            / model_data.get('max_window_used', 1)
            * 100
        )
        overflow_rate = (
            (model_data['overflows'] / model_data['attempts']) * 100
            if model_data['attempts']
            else 0
        )

        return {
            'attempts': model_data['attempts'],
            'overflows': model_data['overflows'],
            'avg_usage_percentage': avg_usage,
            'overflow_rate': overflow_rate,
            'max_window_used': model_data.get('max_window_used'),
        }

    def save_stats(self, file_path: str = 'context_usage_stats.json'):
        """Save context usage statistics to a JSON file"""
        stats_to_save = {
            **self.context_stats,
            'model_details': {
                k: v
                for k, v in self.context_stats['model_usage'].items()
                if not any(key.startswith('_') for key in v)
            },
        }
        Path(file_path).write_text(json.dumps(stats_to_save, indent=2))

    def load_stats(self, file_path: str = 'context_usage_stats.json'):
        """Load context usage statistics from a JSON file"""
        try:
            stats = json.loads(Path(file_path).read_text())
            self.context_stats.update(
                {k: v for k, v in stats.items() if k not in ['model_details']}
            )
            self.context_stats['model_usage'] = {
                k: {k2: v2 for k2, v2 in v.items() if not k2.startswith('_')}
                for k, v in stats.get('model_details', {}).items()
            }
        except (FileNotFoundError, json.JSONDecodeError):
            pass
