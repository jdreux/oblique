import time
from typing import Dict, List, Optional
from collections import deque


class PerformanceMonitor:
    """
    Performance monitoring utility for tracking frame rates and identifying bottlenecks.
    """

    def __init__(self, window_size: int = 60):
        """
        Initialize the performance monitor.

        Args:
            window_size: Number of frames to average for FPS calculation
        """
        self.window_size = window_size
        self.frame_times = deque(maxlen=window_size)
        self.last_frame_time = None
        self.frame_count = 0
        self.start_time = time.time()

        # Performance metrics
        self.min_fps = float("inf")
        self.max_fps = 0.0
        self.avg_fps = 0.0

    def begin_frame(self) -> None:
        """Mark the beginning of a frame."""
        self.last_frame_time = time.time()

    def end_frame(self) -> None:
        """Mark the end of a frame and update metrics."""
        if self.last_frame_time is not None:
            frame_time = time.time() - self.last_frame_time
            self.frame_times.append(frame_time)
            self.frame_count += 1

            # Update FPS metrics
            if len(self.frame_times) >= 2:
                current_fps = 1.0 / frame_time
                self.min_fps = min(self.min_fps, current_fps)
                self.max_fps = max(self.max_fps, current_fps)

                # Calculate average FPS over the window
                avg_frame_time = sum(self.frame_times) / len(self.frame_times)
                self.avg_fps = 1.0 / avg_frame_time

    def get_stats(self) -> Dict[str, float]:
        """
        Get current performance statistics.

        Returns:
            Dictionary containing FPS statistics
        """
        if len(self.frame_times) < 2:
            return {
                "avg_fps": 0.0,
                "min_fps": 0.0,
                "max_fps": 0.0,
                "frame_count": self.frame_count,
                "runtime": time.time() - self.start_time,
            }

        return {
            "avg_fps": self.avg_fps,
            "min_fps": self.min_fps,
            "max_fps": self.max_fps,
            "frame_count": self.frame_count,
            "runtime": time.time() - self.start_time,
            "frame_time_ms": (sum(self.frame_times) / len(self.frame_times)) * 1000,
        }

    def print_stats(self, every_n_frames: int = 60) -> None:
        """
        Print performance statistics every N frames.

        Args:
            every_n_frames: Print stats every N frames
        """
        if self.frame_count % every_n_frames == 0 and self.frame_count > 0:
            stats = self.get_stats()
            print(
                f"Performance: {stats['avg_fps']:.1f} FPS avg, "
                f"{stats['min_fps']:.1f} min, {stats['max_fps']:.1f} max, "
                f"{stats['frame_time_ms']:.1f}ms avg frame time"
            )

    def reset(self) -> None:
        """Reset all performance metrics."""
        self.frame_times.clear()
        self.last_frame_time = None
        self.frame_count = 0
        self.start_time = time.time()
        self.min_fps = float("inf")
        self.max_fps = 0.0
        self.avg_fps = 0.0
