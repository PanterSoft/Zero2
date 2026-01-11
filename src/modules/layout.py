"""
Layout management framework for 128x64 OLED display.
Prevents text and UI elements from overlapping by tracking occupied regions.
"""
from modules.logger import get_logger

logger = get_logger(__name__)


class LayoutRegion:
    """Represents a rectangular region on the display."""

    def __init__(self, x, y, width, height, name=""):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.name = name

    def intersects(self, other):
        """Check if this region intersects with another region."""
        return not (
            self.x + self.width <= other.x or
            other.x + other.width <= self.x or
            self.y + self.height <= other.y or
            other.y + other.height <= self.y
        )

    def __repr__(self):
        return f"LayoutRegion({self.x},{self.y},{self.width}x{self.height},'{self.name}')"


class LayoutManager:
    """
    Manages layout regions on a fixed-size display to prevent overlaps.

    For 128x64 OLED display:
    - Width: 128 pixels
    - Height: 64 pixels
    - Default font: ~6px wide, ~8px tall per character
    """

    def __init__(self, width=128, height=64):
        self.width = width
        self.height = height
        self.regions = []
        self.font_char_width = 6  # Approximate character width for default font
        self.font_char_height = 8  # Approximate character height for default font
        self.line_spacing = 2  # Extra spacing between lines

    def clear(self):
        """Clear all registered regions."""
        self.regions.clear()

    def register_region(self, x, y, width, height, name=""):
        """
        Register a region and check for overlaps.

        Args:
            x: X position (left)
            y: Y position (top)
            width: Width in pixels
            height: Height in pixels
            name: Optional name for debugging

        Returns:
            LayoutRegion if successful, None if overlap detected
        """
        # Validate bounds
        if x < 0 or y < 0 or x + width > self.width or y + height > self.height:
            logger.warning(f"Region {name} ({x},{y},{width}x{height}) exceeds display bounds ({self.width}x{self.height})")
            return None

        region = LayoutRegion(x, y, width, height, name)

        # Check for overlaps
        for existing in self.regions:
            if region.intersects(existing):
                logger.warning(f"Region {name} ({x},{y},{width}x{height}) overlaps with {existing.name} ({existing.x},{existing.y},{existing.width}x{existing.height})")
                return None

        self.regions.append(region)
        return region

    def reserve_text(self, x, y, text, max_width=None, name=""):
        """
        Reserve space for text.

        Args:
            x: X position (left)
            y: Y position (top)
            text: Text string to reserve space for
            max_width: Maximum width (truncates text if needed)
            name: Optional name for debugging

        Returns:
            LayoutRegion if successful, None if overlap detected
        """
        # Calculate text width
        text_width = len(text) * self.font_char_width
        if max_width:
            text_width = min(text_width, max_width)
            # Truncate text if needed
            max_chars = max_width // self.font_char_width
            if len(text) > max_chars:
                text = text[:max_chars]

        text_height = self.font_char_height

        return self.register_region(x, y, text_width, text_height, name or f"text:'{text[:20]}'")

    def reserve_line(self, y, line_height=None, name=""):
        """
        Reserve a full-width line at a specific Y position.

        Args:
            y: Y position (top)
            line_height: Height of the line (default: font_char_height + line_spacing)
            name: Optional name for debugging

        Returns:
            LayoutRegion if successful, None if overlap detected
        """
        if line_height is None:
            line_height = self.font_char_height + self.line_spacing

        return self.register_region(0, y, self.width, line_height, name or f"line:{y}")

    def reserve_column(self, x, width, name=""):
        """
        Reserve a full-height column at a specific X position.

        Args:
            x: X position (left)
            width: Width of the column
            name: Optional name for debugging

        Returns:
            LayoutRegion if successful, None if overlap detected
        """
        return self.register_region(x, 0, width, self.height, name or f"column:{x}")

    def reserve_area(self, x, y, width, height, name=""):
        """
        Reserve a rectangular area.

        Args:
            x: X position (left)
            y: Y position (top)
            width: Width in pixels
            height: Height in pixels
            name: Optional name for debugging

        Returns:
            LayoutRegion if successful, None if overlap detected
        """
        return self.register_region(x, y, width, height, name)

    def get_available_y(self, start_y, line_height=None):
        """
        Find the next available Y position below start_y that doesn't overlap.

        Args:
            start_y: Starting Y position
            line_height: Height of the line to place

        Returns:
            Available Y position
        """
        if line_height is None:
            line_height = self.font_char_height + self.line_spacing

        test_y = start_y
        max_iterations = 100  # Prevent infinite loops

        for _ in range(max_iterations):
            test_region = LayoutRegion(0, test_y, self.width, line_height, "test")
            overlaps = False

            for existing in self.regions:
                if test_region.intersects(existing):
                    overlaps = True
                    test_y = existing.y + existing.height
                    break

            if not overlaps:
                return test_y

        logger.warning(f"Could not find available Y position after {max_iterations} iterations")
        return test_y

    def get_available_x(self, y, width, start_x=0):
        """
        Find the next available X position at a given Y that doesn't overlap.

        Args:
            y: Y position
            width: Width needed
            start_x: Starting X position

        Returns:
            Available X position
        """
        test_x = start_x
        max_iterations = 100

        for _ in range(max_iterations):
            test_region = LayoutRegion(test_x, y, width, self.font_char_height, "test")
            overlaps = False

            for existing in self.regions:
                if test_region.intersects(existing):
                    overlaps = True
                    test_x = existing.x + existing.width + 2  # 2px gap
                    break

            if not overlaps:
                if test_x + width <= self.width:
                    return test_x
                else:
                    # No space on this line, try next line
                    return None

        logger.warning(f"Could not find available X position after {max_iterations} iterations")
        return test_x

    def get_regions(self):
        """Get all registered regions."""
        return self.regions.copy()

    def get_summary(self):
        """Get a summary of all registered regions."""
        summary = f"Layout Manager ({self.width}x{self.height}):\n"
        for region in self.regions:
            summary += f"  {region}\n"
        return summary
