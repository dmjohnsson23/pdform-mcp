import pymupdf
from typing import Mapping


def rect_to_dict(rect: pymupdf.Rect) -> Mapping:
    return {'left': rect.x0, 'right': rect.x1, 'top': rect.y0, 'bottom': rect.y1}