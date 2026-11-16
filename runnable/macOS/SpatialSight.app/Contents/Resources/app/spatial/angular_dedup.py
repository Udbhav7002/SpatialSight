"""
Angular Deduplication - Spatial deduplication of detected objects across keyframes.

When the same physical object (e.g., a chair) appears in multiple keyframes
taken from different angles, this module merges them into a single unique
object using angular proximity in world coordinates.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SpatialObject:
    """A unique physical object in the room after deduplication."""
    object_id: int
    class_name: str
    world_angle: float           # Estimated azimuth in degrees (0-360)
    confidence: float            # Best confidence across all sightings
    sighting_count: int = 1      # How many keyframes this object appeared in
    keyframe_indices: list[int] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"SpatialObject(id={self.object_id}, class='{self.class_name}', "
            f"angle={self.world_angle:.1f} deg, conf={self.confidence:.2f}, "
            f"sightings={self.sighting_count})"
        )


class AngularDeduplicator:
    """
    Deduplicates detected objects across multiple keyframes using angular proximity.

    Two detections of the same class are considered the SAME physical object if
    their estimated world angles are within `merge_threshold` degrees of each other.

    Example:
        - Keyframe 1 (yaw=10 deg): detects "chair" at world angle 25 deg
        - Keyframe 2 (yaw=40 deg): detects "chair" at world angle 28 deg
        - deltaangle = 3 deg < threshold (15 deg) -> SAME chair -> merged

        - Keyframe 3 (yaw=170 deg): detects "chair" at world angle 155 deg
        - deltaangle from chair-1 = 130 deg > threshold -> DIFFERENT chair -> new object
    """

    def __init__(self, merge_threshold: float = 15.0):
        """
        Args:
            merge_threshold: Maximum angular difference (degrees) for two
                             detections of the same class to be considered
                             the same physical object.
        """
        self.merge_threshold = merge_threshold
        self._objects: list[SpatialObject] = []
        self._next_id: int = 0

    def reset(self) -> None:
        """Clear all tracked objects for a new scan."""
        self._objects.clear()
        self._next_id = 0

    def add_detection(
        self,
        class_name: str,
        world_angle: float,
        confidence: float,
        keyframe_index: int,
    ) -> SpatialObject:
        """
        Add a detection and either merge it with an existing object or create a new one.

        Args:
            class_name: Detected object class (e.g., "chair").
            world_angle: Estimated world angle in degrees (0-360).
            confidence: Detection confidence (0.0 - 1.0).
            keyframe_index: Index of the keyframe this detection came from.

        Returns:
            The SpatialObject this detection was assigned to (existing or new).
        """
        # Search for an existing object of the same class within merge threshold
        best_match: SpatialObject | None = None
        best_delta: float = float("inf")

        for obj in self._objects:
            if obj.class_name != class_name:
                continue

            delta = abs(self._angle_diff(world_angle, obj.world_angle))
            if delta < self.merge_threshold and delta < best_delta:
                best_match = obj
                best_delta = delta

        if best_match is not None:
            # Merge with existing object
            best_match.sighting_count += 1
            best_match.confidence = max(best_match.confidence, confidence)
            if keyframe_index not in best_match.keyframe_indices:
                best_match.keyframe_indices.append(keyframe_index)

            logger.debug(
                f"Merged '{class_name}' at {world_angle:.1f} deg with object "
                f"{best_match.object_id} (delta={best_delta:.1f} deg)"
            )
            return best_match
        else:
            # Create new unique object
            new_obj = SpatialObject(
                object_id=self._next_id,
                class_name=class_name,
                world_angle=world_angle,
                confidence=confidence,
                sighting_count=1,
                keyframe_indices=[keyframe_index],
            )
            self._objects.append(new_obj)
            self._next_id += 1

            logger.debug(
                f"New object #{new_obj.object_id}: '{class_name}' at {world_angle:.1f} deg"
            )
            return new_obj

    def get_unique_objects(self) -> list[SpatialObject]:
        """Return all unique physical objects found in the room."""
        return self._objects.copy()

    def get_inventory(self) -> dict[str, int]:
        """
        Get a deduplicated count of objects by class.

        Returns:
            Dict mapping class names to unique counts.
            Example: {"chair": 2, "table": 1, "monitor": 1, "person": 3}
        """
        counts: dict[str, int] = {}
        for obj in self._objects:
            counts[obj.class_name] = counts.get(obj.class_name, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def get_total_unique_count(self) -> int:
        """Get the total number of unique physical objects detected."""
        return len(self._objects)

    def get_summary(self) -> str:
        """Get a human-readable summary of the room inventory."""
        inventory = self.get_inventory()
        if not inventory:
            return "No objects detected."

        lines = ["ROOM INVENTORY (Deduplicated)"]
        lines.append("-" * 35)
        for cls, count in inventory.items():
            dots = "." * (25 - len(cls))
            lines.append(f"  - {cls} {dots} {count}")
        lines.append("-" * 35)
        lines.append(f"  Total Unique Objects: {self.get_total_unique_count()}")
        return "\n".join(lines)

    @staticmethod
    def _angle_diff(a: float, b: float) -> float:
        """Shortest angular difference (handles wraparound)."""
        diff = (a - b + 180) % 360 - 180
        return diff
