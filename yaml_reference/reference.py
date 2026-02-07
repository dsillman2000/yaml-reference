from pathlib import Path
from typing import (
    Any,
    Callable,
    Generic,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from ruamel.yaml import Constructor, MappingNode, Node
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.constructor import RoundTripConstructor

from yaml_reference.errors import ConstructorException

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
        raise NotImplementedError("Subclasses must implement this method")


class Reference(Resolvable[Any]):
    """
    A class to represent a reference in a YAML file.

    Attributes:
        path (str): The path to the referenced file.
    """

    __local_file__: Path
    path: Path

    def __init__(
        self,
        local_file: Path,
        path: str,
    ):
        """
        Initialize the Reference object with a path.

        Args:
            local_file (Path): The path to the local file containing the reference.
            path (str): The path argument of the reference.
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
        return f'Reference("path={self.path.relative_to(self.__local_file__.parent)}")'

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the Reference object to a dictionary.

        Returns:
            dict[str, Any]: The dictionary representation of the Reference object.
        """
        path_dict = {"path": str(self.path.relative_to(self.__local_file__.parent))}
        return path_dict

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
        if constructor is None or not hasattr(constructor, "stream_name"):
            raise ConstructorException(
                "Constructor does not have a 'stream_name' attribute."
            )
        local_file = Path(constructor.stream_name)  # type: ignore
        if not isinstance(node, MappingNode):
            raise ConstructorException(f"Invalid node type: {type(node)}")
        if isinstance(constructor, RoundTripConstructor):
            data = CommentedMap()
            constructor.construct_mapping(node, maptyp=data)
        else:
            data = constructor.construct_mapping(node)
        return cls(local_file, **data)

    def resolve(self, yaml: Any) -> Any:
        """
        Resolve the reference and return the resolved value.

        Args:
            loader (YAML): The YAML loader.

        Returns:
            Any: The resolved value of the reference.
        """
        if self.resolved:
            return self.__resolved_value__

        try:
            data = yaml.load(self.path.open("r"))
        except Exception as e:
            raise ConstructorException(
                f"Failed to resolve reference: {self.path.absolute()}\nException:\n{e}"
            ) from e
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
    paths: list[Path]  # List of paths matching the glob pattern

    def __init__(self, local_file: Path, glob: str):
        """
        Initialize the ReferenceAll object with a glob pattern.

        Args:
            local_file (Path): The path to the local file containing the reference.
            glob (str): The glob pattern to match files.
        """
        self.__resolved__ = False
        self.__resolved_value__ = []
        self.__local_file__ = local_file
        self.glob = glob
        self.paths = list(local_file.parent.glob(glob))
        self.paths = sorted(self.paths, key=lambda p: str(p.absolute()))

    def __repr__(self) -> str:
        """
        Return a string representation of the ReferenceAll object.

        Returns:
            str: The string representation of the ReferenceAll object.
        """
        return f'ReferenceAll(glob="{self.glob}")'

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
        if constructor is None or not hasattr(constructor, "stream_name"):
            raise ConstructorException(
                f"Constructor {constructor} does not have a 'stream_name' attribute."
            )

        local_file = Path(constructor.stream_name)  # type: ignore
        if not isinstance(node, MappingNode):
            raise ConstructorException(f"Invalid node type: {type(node)}")
        if isinstance(constructor, RoundTripConstructor):
            data = CommentedMap()
            constructor.construct_mapping(node, maptyp=data)
        else:
            data = constructor.construct_mapping(node)
        return cls(local_file, **data)

    def resolve(self, yaml: Any) -> Any:
        """
        Resolve the reference and return the resolved value.

        Args:
            yaml (YAML): The YAML loader.

        Returns:
            Any: The resolved value of the reference.
        """
        if self.resolved:
            return self.__resolved_value__

        data = [yaml.load(path.open("r")) for path in self.paths]
        if not data:
            raise ConstructorException(f"Failed to resolve reference: {self.glob}")
        self.__resolved_value__ = data
        self.__resolved__ = True
        return self.__resolved_value__


def resolve(yaml, data: Any) -> Any:
    """
    Resolve a reference.

    Args:
        yaml (YAML): The YAML loader.
        data (Any): The reference to resolve.

    Returns:
        Any: The resolved data.
    """
    if hasattr(data, "__resolved__") and hasattr(data, "resolve"):
        return data.resolve(yaml)
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
            return {
                key: recursively_resolve(yaml, value) for key, value in data.items()
            }
        elif isinstance(data, Resolvable):
            return resolve(yaml, data)
        else:
            return data
    except ConstructorException as e:
        raise ConstructorException(f"Error resolving reference: {e}") from e
    except Exception as e:
        raise ConstructorException(f"Unexpected error: {e}") from e


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
