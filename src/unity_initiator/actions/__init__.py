from ..utils.pkg_utils import import_submodules_classes

_mods, _classes = import_submodules_classes(__name__)
globals().update(_classes)


__all__ = ["ACTION_MAP"]
__all__.extend((_mods | _classes).keys())


# dynamically generate action map
ACTION_MAP = {
    _class.__module__.split(".")[-1]: _class
    for _class_name, _class in _classes.items()
    if _class_name != "Action"
}
