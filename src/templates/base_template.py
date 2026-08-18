class BaseTemplate:
    def draw_item(self, painter, x, y, length, angle, color, width, **kwargs):
        """Every template implements this single method."""
        raise NotImplementedError