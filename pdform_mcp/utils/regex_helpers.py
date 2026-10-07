import re
__all__ = ("regex_registry",)

class RegexRegistry:
    """
    Utility to compile and cache regexes.
    """
    def __init__(self):
        self.registry = {}

    def __getitem__(self, key)->re.Pattern:
        regex = self.registry.get(key)
        if regex is not None:
            return regex
        regex = re.compile(key)
        self.registry[key] = regex
        return regex

regex_registry = RegexRegistry()