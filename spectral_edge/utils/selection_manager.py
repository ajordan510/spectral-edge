"""
Selection Manager

Manages saved and recent channel selections for the Flight Navigator.
Provides persistence across sessions using JSON files.

Author: SpectralEdge Development Team
Date: 2026-01-27
"""

import json
import os
from typing import List, Tuple, Dict, Optional, Any
from pathlib import Path
from datetime import datetime


class SelectionManager:
    """
    Manages saved and recent channel selections for the Flight Navigator.
    
    This class provides functionality to:
    - Save named selections for later use
    - Track recent selections automatically
    - Persist selections across sessions using JSON files
    
    Attributes:
    -----------
    config_dir : Path
        Directory for configuration files
    recent_file : Path
        Path to recent selections JSON file
    saved_file : Path
        Path to saved selections JSON file
    max_recent : int
        Maximum number of recent selections to keep
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize selection manager.
        
        Parameters:
        -----------
        config_dir : str, optional
            Directory for configuration files (default: ~/.spectral_edge)
        """
        if config_dir is None:
            config_dir = os.path.expanduser('~/.spectral_edge')
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.recent_file = self.config_dir / 'recent_selections.json'
        self.saved_file = self.config_dir / 'saved_selections.json'
        
        self.max_recent = 10
    
    def save_selection(self, name: str, selection_data: Any) -> None:
        """
        Save a named selection.
        
        Parameters:
        -----------
        name : str
            Name for the selection
        selection_data : Any
            Selection data (dict with 'items' and optional 'view_mode')
        """
        saved = self._load_saved()
        
        # Create/update entry
        saved[name] = {
            'data': selection_data,
            'timestamp': self._get_timestamp()
        }
        
        # Save
        self._save_saved(saved)
    
    def load_selection(self, name: str) -> Optional[Dict]:
        """
        Load a saved selection by name.
        
        Parameters:
        -----------
        name : str
            Name of the selection to load
        
        Returns:
        --------
        dict or None
            Selection data if found, None otherwise
        """
        saved = self._load_saved()
        if name in saved:
            return saved[name].get('data', saved[name])
        return None
    
    def add_recent_selection(self, description: str, selection_data: Any) -> None:
        """
        Add a selection to recent history.
        
        Parameters:
        -----------
        description : str
            Description of the selection
        selection_data : Any
            Selection data (dict with 'items' and optional 'view_mode')
        """
        recent = self._load_recent()
        
        # Create selection entry
        entry = {
            'name': description,
            'data': selection_data,
            'timestamp': self._get_timestamp()
        }
        
        # Add to front
        recent.insert(0, entry)
        
        # Keep only max_recent entries
        recent = recent[:self.max_recent]
        
        # Save
        self._save_recent(recent)
    
    def get_recent_selections(self) -> List[Dict]:
        """
        Get list of recent selections.
        
        Returns:
        --------
        list of dict
            List of selection dictionaries with 'name', 'data', 'timestamp'
        """
        return self._load_recent()
    
    def get_saved_selections(self) -> Dict[str, Dict]:
        """
        Get dictionary of saved selections.
        
        Returns:
        --------
        dict
            Dictionary mapping names to selection dictionaries
        """
        return self._load_saved()
    
    def delete_saved_selection(self, name: str) -> None:
        """
        Delete a saved selection.
        
        Parameters:
        -----------
        name : str
            Name of the selection to delete
        """
        saved = self._load_saved()
        if name in saved:
            del saved[name]
            self._save_saved(saved)
    
    def _load_recent(self) -> List[Dict]:
        """Load recent selections from file."""
        if not self.recent_file.exists():
            return []
        
        try:
            with open(self.recent_file, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    
    def _save_recent(self, recent: List[Dict]) -> None:
        """Save recent selections to file."""
        try:
            with open(self.recent_file, 'w') as f:
                json.dump(recent, f, indent=2)
        except Exception:
            pass  # Silently fail if can't save
    
    def _load_saved(self) -> Dict[str, Dict]:
        """Load saved selections from file."""
        if not self.saved_file.exists():
            return {}
        
        try:
            with open(self.saved_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_saved(self, saved: Dict[str, Dict]) -> None:
        """Save saved selections to file."""
        try:
            with open(self.saved_file, 'w') as f:
                json.dump(saved, f, indent=2)
        except Exception:
            pass  # Silently fail if can't save
    
    def _get_timestamp(self) -> str:
        """Get current timestamp string."""
        return datetime.now().isoformat()
