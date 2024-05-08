import importlib
import inspect
import pkgutil
import sys


def import_submodules(package_name):
    package = sys.modules[package_name]
    return {
        name: importlib.import_module(package_name + "." + name)
        for loader, name, is_pkg in pkgutil.walk_packages(package.__path__)
    }


def import_submodules_classes(package_name):
    package = sys.modules[package_name]
    modules = {}
    classes = {}
    for pkg_info in pkgutil.walk_packages(package.__path__):
        name = pkg_info[1]
        pkg_name = package_name + "." + name
        module = importlib.import_module(pkg_name)
        modules[pkg_name] = module
        for member_name, obj in inspect.getmembers(module):
            if member_name not in module.__dict__.get("__all__", []):
                continue
            if inspect.isclass(obj) and obj.__module__ == module.__name__:
                classes[member_name] = obj
    return modules, classes
