"""
Progress Tracking Module for Batch Processing

This module provides detailed progress tracking with per-channel updates,
estimated time remaining, and throughput statistics.

Author: SpectralEdge Development Team
Date: 2026-02-02
"""

import time
from typing import Optional, Callable
from dataclasses import dataclass


@dataclass
class ProgressInfo:
    """Container for detailed progress information."""
    current_channel: int
    total_channels: int
    current_event: str
    flight_key: str
    channel_key: str
    percent_complete: float
    elapsed_time: float
    estimated_time_remaining: float
    channels_per_second: float
    
    def __str__(self) -> str:
        """Format progress info as human-readable string."""
        return (
            f"Channel {self.current_channel}/{self.total_channels} "
            f"({self.percent_complete:.1f}%) - "
            f"{self.flight_key}/{self.channel_key} - "
            f"Event: {self.current_event} - "
            f"ETA: {self.estimated_time_remaining:.1f}s"
        )


class ProgressTracker:
    """
    Tracks batch processing progress with detailed statistics.
    
    Provides per-channel progress updates, estimated time remaining,
    and throughput metrics.
    """
    
    def __init__(self, total_channels: int, progress_callback: Optional[Callable] = None):
        """
        Initialize progress tracker.
        
        Parameters:
        -----------
        total_channels : int
            Total number of channels to process
        progress_callback : callable, optional
            Callback function to receive progress updates
            Signature: callback(progress_info: ProgressInfo)
        """
        self.total_channels = total_channels
        self.progress_callback = progress_callback
        
        self.current_channel = 0
        self.start_time = time.time()
        self.channel_start_times = []
        
        self.current_flight = ""
        self.current_channel_key = ""
        self.current_event = ""
        
    def start_channel(self, flight_key: str, channel_key: str):
        """
        Mark the start of processing a new channel.
        
        Parameters:
        -----------
        flight_key : str
            Flight identifier
        channel_key : str
            Channel identifier
        """
        self.current_channel += 1
        self.current_flight = flight_key
        self.current_channel_key = channel_key
        self.channel_start_times.append(time.time())
        
        self._emit_progress()
    
    def update_event(self, event_name: str):
        """
        Update the current event being processed.
        
        Parameters:
        -----------
        event_name : str
            Event name
        """
        self.current_event = event_name
        self._emit_progress()
    
    def finish_channel(self):
        """
        Mark the current channel as finished.
        
        This method emits a final progress update for the completed channel.
        """
        self._emit_progress()
    
    def _emit_progress(self):
        """Calculate and emit progress information."""
        if self.progress_callback is None:
            return
        
        elapsed_time = time.time() - self.start_time
        percent_complete = (self.current_channel / self.total_channels) * 100
        
        # Calculate estimated time remaining
        if self.current_channel > 0 and elapsed_time > 0:
            avg_time_per_channel = elapsed_time / self.current_channel
            remaining_channels = self.total_channels - self.current_channel
            estimated_time_remaining = avg_time_per_channel * remaining_channels
            channels_per_second = self.current_channel / elapsed_time
        else:
            estimated_time_remaining = 0.0
            channels_per_second = 0.0
        
        progress_info = ProgressInfo(
            current_channel=self.current_channel,
            total_channels=self.total_channels,
            current_event=self.current_event,
            flight_key=self.current_flight,
            channel_key=self.current_channel_key,
            percent_complete=percent_complete,
            elapsed_time=elapsed_time,
            estimated_time_remaining=estimated_time_remaining,
            channels_per_second=channels_per_second
        )
        
        self.progress_callback(progress_info)
    
    def get_summary(self) -> dict:
        """
        Get processing summary statistics.
        
        Returns:
        --------
        dict
            Summary statistics including total time, throughput, etc.
        """
        total_time = time.time() - self.start_time
        
        return {
            'total_channels': self.total_channels,
            'channels_processed': self.current_channel,
            'total_time_seconds': total_time,
            'average_time_per_channel': total_time / max(self.current_channel, 1),
            'channels_per_second': self.current_channel / max(total_time, 0.001)
        }
