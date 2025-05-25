from pathlib import Path
from typing import Any, Callable, Generic, Protocol, TypeVar, runtime_checkable

from ruamel.yaml import BaseConstructor, Constructor, MappingNode, Node, Representer

from yaml_reference.errors import ConstructorException, RepresenterException

T = TypeVar("T")


@runtime_checkable
class Resolvable(Protocol, Generic[T]):
    """
    A protocol that defines a method for resolving a reference.

    Attributes:
        __resolved__ (bool): Indicates whether the reference has been resolved.
        __resolved_value__ (T): The resolved value of the reference.

    Methods:
        resolve() -> T: Resolves the reference.
    """

    __resolved__: bool
    __resolved_value__: T

    @property
    def resolved(self) -> bool:
        """
        Indicates whether the reference has been resolved.

        Returns:
            bool: True if the reference is resolved, False otherwise.
        """
        return self.__resolved__

    def resolve(self, yaml) -> T:
        """
        Resolves the reference.

        Returns:
            T: The resolved value of the reference.
        """
        pass


class Reference(Resolvable[Any]):
    """
    A class to represent a reference in a YAML file.

    Attributes:
        path (str): The path to the referenced file.
    """

    __local_file__: Path
    path: Path

    def __init__(self, local_file: Path, path: str):
        """
        Initialize the Reference object with a path.

        Args:
            path (str): The path to the referenced file.
        """
        self.__resolved__ = False
        self.__resolved_value__ = None
        self.__local_file__ = local_file
        self.path = local_file.parent / path

    def __repr__(self) -> str:
        """
        Return a string representation of the Reference object.

        Returns:
            str: The string representation of the Reference object.
        """
        return f"Reference(path={self.path.relative_to(self.__local_file__.parent)})"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the Reference object to a dictionary.

        Returns:
            dict[str, Any]: The dictionary representation of the Reference object.
        """
        return {"path": str(self.path.relative_to(self.__local_file__.parent))}

    @classmethod
    def from_yaml(cls, constructor: Constructor, node: Node) -> "Reference":
        """
        Create a Reference object from a YAML node.

        Args:
            constructor (Constructor): The YAML constructor.
            node (Node): The YAML node.

        Returns:
            Reference: The created Reference object.
        """
        local_file = Path(constructor.loader.reader.stream.name)
        if not isinstance(node, MappingNode):
            raise ConstructorException(f"Invalid node type: {type(node)}")
        dict_reference = BaseConstructor.construct_mapping(constructor, node)  # construct_mapping(node, maptyp={})
        return cls(local_file, **dict_reference)

    @classmethod
    def to_yaml(cls, representer: Representer, node: "Reference") -> Node:
        """
        Convert a Reference object to a YAML node.

        Args:
            representer (Representer): The YAML representer.
            node (Reference): The Reference object.

        Returns:
            Node: The YAML node representing the Reference object.
        """
        if not isinstance(node, Reference):
            raise RepresenterException(f"Invalid node type: {type(node)}")
        return representer.represent_scalar("!reference", node.to_dict(), style="flow")

    def resolve(self, loader: Any) -> Any:
        """
        Resolve the reference and return the resolved value.

        Args:
            loader (YAML): The YAML loader.

        Returns:
            Any: The resolved value of the reference.
        """
        if self.resolved:
            return self.__resolved_value__

        data = loader.load(self.path.open("r"))
        if not data:
            raise ConstructorException(f"Failed to resolve reference: {self.path.absolute()}")
        # setattr(data, "__resolvable__", self)
        self.__resolved_value__ = data
        self.__resolved__ = True
        return self.__resolved_value__


class ReferenceAll(Resolvable[list[Any]]):
    """
    A class to represent a reference to all YAML files matching a glob pattern.

    Attributes:
        path (str): The path to the referenced file.
    """

    __local_file__: Path
    glob: str
    paths: list[Path]

    def __init__(self, local_file: Path, glob: str):
        """
        Initialize the ReferenceAll object with a glob pattern.

        Args:
            glob (str): The glob pattern to match files.
        """
        self.__resolved__ = False
        self.__resolved_value__ = None
        self.__local_file__ = local_file
        self.glob = glob
        self.paths = list(local_file.parent.glob(glob))

    def __repr__(self) -> str:
        """
        Return a string representation of the ReferenceAll object.

        Returns:
            str: The string representation of the ReferenceAll object.
        """
        return f"ReferenceAll(glob={self.glob})"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the ReferenceAll object to a dictionary.

        Returns:
            dict[str, Any]: The dictionary representation of the ReferenceAll object.
        """
        return {"glob": str(self.glob)}

    @classmethod
    def from_yaml(cls, constructor: Constructor, node: Node) -> "ReferenceAll":
        """
        Create a ReferenceAll object from a YAML node.

        Args:
            constructor (Constructor): The YAML constructor.
            node (Node): The YAML node.

        Returns:
            ReferenceAll: The created ReferenceAll object.
        """
        local_file = Path(constructor.loader.reader.stream.name)
        if not isinstance(node, MappingNode):
            raise ConstructorException(f"Invalid node type: {type(node)}")
        dict_reference = BaseConstructor.construct_mapping(constructor, node)
        return cls(local_file, **dict_reference)

    @classmethod
    def to_yaml(cls, representer: Representer, node: "ReferenceAll") -> Node:
        """
        Convert a ReferenceAll object to a YAML node.

        Args:
            representer (Representer): The YAML representer.
            node (ReferenceAll): The ReferenceAll object.

        Returns:
            Node: The YAML node representing the ReferenceAll object.
        """
        if not isinstance(node, ReferenceAll):
            raise RepresenterException(f"Invalid node type: {type(node)}")
        return representer.represent_scalar("!reference-all", node.to_dict(), style="flow")

    def resolve(self, loader: Any) -> Any:
        """
        Resolve the reference and return the resolved value.

        Args:
            loader (YAML): The YAML loader.

        Returns:
            Any: The resolved value of the reference.
        """
        if self.resolved:
            return self.__resolved_value__

        data = []
        for path in self.paths:
            data.append(loader.load(path.open("r")))
        if not data:
            raise ConstructorException(f"Failed to resolve reference: {self.glob}")
        # setattr(data, "__resolvable__", self)
        self.__resolved_value__ = data
        self.__resolved__ = True
        return self.__resolved_value__


def unresolve(data: Any) -> Any:
    """
    Unresolve a resolved value.

    Args:
        data (Any): The resolved value to unresolve.

    Returns:
        Any: The unresolved data.
    """
    if hasattr(data, "__resolvable__"):
        return data.__resolvable__
    return data


def recursively_resolve(yaml: Any, data: Any) -> Any:
    """
    Recursively resolve all references in the given data.

    Args:
        yaml (YAML): The YAML loader.
        data (Any): The data to resolve references in.

    Returns:
        Any: The data with all references resolved.
    """
    try:
        if isinstance(data, list):
            return [recursively_resolve(yaml, item) for item in data]
        elif isinstance(data, dict):
            return {key: recursively_resolve(yaml, value) for key, value in data.items()}
        elif isinstance(data, Resolvable):
            return data.resolve(yaml)
        else:
            return data
    except ConstructorException as e:
        raise ConstructorException(f"Error resolving reference: {e}") from e
    except Exception as e:
        raise ConstructorException(f"Unexpected error: {e}") from e


def recursively_unresolve(data: Any) -> Any:
    """
    Recursively unresolve all references in the given data.

    Args:
        data (Any): The data to unresolve references in.

    Returns:
        Any: The data with all references unresolved.
    """
    try:
        if isinstance(data, list):
            return [recursively_unresolve(item) for item in data]
        elif isinstance(data, dict):
            return {key: recursively_unresolve(value) for key, value in data.items()}
        elif isinstance(data, Resolvable):
            return unresolve(data)
        else:
            return data
    except RepresenterException as e:
        raise RepresenterException(f"Error unresolving reference: {e}") from e
    except Exception as e:
        raise RepresenterException(f"Unexpected error: {e}") from e


def recursively_resolve_after(yaml, func: Callable) -> Callable:
    """Decorator to resolve data after a function call.

    Args:
        yaml (YAML): The YAML loader.
        func (Callable): Function to be decorated.

    Returns:
        Callable: Decorated function.
    """

    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return recursively_resolve(yaml, result)

    return wrapper


def recursively_unresolve_before(func: Callable) -> Callable:
    """Decorator to unresolve data before a function call.

    Args:
        func (Callable): Function to be decorated.

    Returns:
        Callable: Decorated function.
    """

    def wrapper(*args, **kwargs):
        result = recursively_unresolve(args[0])
        args = (result,) + args[1:]
        return func(*args, **kwargs)

    return wrapper
