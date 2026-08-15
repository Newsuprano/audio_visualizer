class BaseTemplate:
    def draw_item(self, painter, x, y, length, angle, color, width):
        """Every template implements this single method."""
        raise NotImplementedError