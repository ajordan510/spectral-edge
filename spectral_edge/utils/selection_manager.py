"""
Selection Manager

Manages saved and recent channel selections for the Flight Navigator.
Provides persistence across sessions using JSON files.

Author: SpectralEdge Development Team
Date: 2026-01-27
"""

import json
import os
from typing import List, Tuple, Dict, Optional
from pathlib import Path


class SelectionManager:
    """Manages saved and recent channel selections."""
    
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
    
    def add_recent_selection(self, selection: List[Tuple[str, str]], description: str = ""):
        """
        Add a selection to recent history.
        
        Parameters:
        -----------
        selection : list of tuples
            List of (flight_key, channel_key) tuples
        description : str, optional
            Description of the selection
        """
        recent = self._load_recent()
        
        # Create selection entry
        entry = {
            'selection': [(f, c) for f, c in selection],
            'description': description or f"{len(selection)} channels",
            'timestamp': self._get_timestamp()
        }
        
        # Remove duplicates (same channels)
        recent = [r for r in recent if r['selection'] != entry['selection']]
        
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
            List of selection dictionaries with 'selection', 'description', 'timestamp'
        """
        return self._load_recent()
    
    def save_selection(self, name: str, selection: List[Tuple[str, str]], description: str = ""):
        """
        Save a named selection.
        
        Parameters:
        -----------
        name : str
            Name for the selection
        selection : list of tuples
            List of (flight_key, channel_key) tuples
        description : str, optional
            Description of the selection
        """
        saved = self._load_saved()
        
        # Create/update entry
        saved[name] = {
            'selection': [(f, c) for f, c in selection],
            'description': description,
            'timestamp': self._get_timestamp()
        }
        
        # Save
        self._save_saved(saved)
    
    def get_saved_selections(self) -> Dict[str, Dict]:
        """
        Get dictionary of saved selections.
        
        Returns:
        --------
        dict
            Dictionary mapping names to selection dictionaries
        """
        return self._load_saved()
    
    def delete_saved_selection(self, name: str):
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
    
    def export_selection(self, name: str, filepath: str):
        """
        Export a saved selection to a JSON file.
        
        Parameters:
        -----------
        name : str
            Name of the selection to export
        filepath : str
            Path to export file
        """
        saved = self._load_saved()
        if name not in saved:
            raise ValueError(f"Selection '{name}' not found")
        
        with open(filepath, 'w') as f:
            json.dump(saved[name], f, indent=2)
    
    def import_selection(self, name: str, filepath: str):
        """
        Import a selection from a JSON file.
        
        Parameters:
        -----------
        name : str
            Name for the imported selection
        filepath : str
            Path to import file
        """
        with open(filepath, 'r') as f:
            selection_data = json.load(f)
        
        # Validate format
        if 'selection' not in selection_data:
            raise ValueError("Invalid selection file format")
        
        # Save with new name
        saved = self._load_saved()
        saved[name] = selection_data
        self._save_saved(saved)
    
    def _load_recent(self) -> List[Dict]:
        """Load recent selections from file."""
        if not self.recent_file.exists():
            return []
        
        try:
            with open(self.recent_file, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def _save_recent(self, recent: List[Dict]):
        """Save recent selections to file."""
        with open(self.recent_file, 'w') as f:
            json.dump(recent, f, indent=2)
    
    def _load_saved(self) -> Dict[str, Dict]:
        """Load saved selections from file."""
        if not self.saved_file.exists():
            return {}
        
        try:
            with open(self.saved_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_saved(self, saved: Dict[str, Dict]):
        """Save saved selections to file."""
        with open(self.saved_file, 'w') as f:
            json.dump(saved, f, indent=2)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime
        return datetime.now().isoformat()
