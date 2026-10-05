import pymupdf
from typing import Mapping


def rect_to_list(rect: pymupdf.Rect) -> tuple[float,float,float,float]:
    return (rect.x0, rect.y0, rect.x1, rect.y1)


def quad_to_list(quad: pymupdf.Quad) -> tuple[tuple[float,float],tuple[float,float],tuple[float,float],tuple[float,float]]:
    return (
        (quad.ul.x, quad.ul.y), 
        (quad.ur.x, quad.ur.y), 
        (quad.ll.x, quad.ll.y), 
        (quad.lr.x, quad.lr.y),
    )