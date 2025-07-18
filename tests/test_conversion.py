import os
import pytest
import enum
from typing import Any, Union, Optional, TYPE_CHECKING
from pydantic import ValidationError

from pydantic_rpc import Message
from pydantic_rpc.core import (
    generate_proto,
    generate_and_compile_proto,
    convert_python_message_to_proto,
    generate_message_converter,
    is_skip_generation,
)

from unittest import mock


if TYPE_CHECKING:

    class Node:
        unique_package_name: str = ""

    class FixtureRequest:
        node: Node = Node()
else:
    from pytest import FixtureRequest


class Color(enum.Enum):
    RED = 0
    GREEN = 1
    BLUE = 2


def test_primitive_types_only():
    """Test message with only primitive types."""

    class PrimitiveMessage(Message):
        text: str
        number: int
        flag: bool
        price: float
        data: bytes

    # Test proto generation using a dummy service
    class DummyService:
        def test_method(self, req: PrimitiveMessage) -> PrimitiveMessage:
            return req

    proto = generate_proto(DummyService())
    assert "string text = 1;" in proto
    assert "int32 number = 2;" in proto
    assert "bool flag = 3;" in proto
    assert "float price = 4;" in proto
    assert "bytes data = 5;" in proto


def test_union_type_only():
    """Test message with only union types (oneof)."""

    class UnionMessage(Message):
        value: Union[str, int, bool]

    # Test proto generation using a dummy service
    class DummyService:
        def test_method(self, req: UnionMessage) -> UnionMessage:
            return req

    proto = generate_proto(DummyService())
    assert "oneof value {" in proto
    assert "string value_string = 1;" in proto
    assert "int32 value_int32 = 2;" in proto
    assert "bool value_bool = 3;" in proto


def test_primitive_and_union():
    """Test message with both primitive and union types."""

    class MixedMessage(Message):
        name: str
        value: Union[str, int]
        active: bool

    # Test proto generation using a dummy service
    class DummyService:
        def test_method(self, req: MixedMessage) -> MixedMessage:
            return req

    proto = generate_proto(DummyService())
    assert "string name = 1;" in proto
    assert "oneof value {" in proto
    assert "string value_string = 2;" in proto
    assert "int32 value_int32 = 3;" in proto
    assert "bool active = 4;" in proto


def test_optional_with_none():
    """Test optional fields (Union with None)."""

    class OptionalMessage(Message):
        required_field: str
        optional_field: Optional[str]
        optional_int: Optional[int]

    # Test proto generation using a dummy service
    class DummyService:
        def test_method(self, req: OptionalMessage) -> OptionalMessage:
            return req

    proto = generate_proto(DummyService())
    assert "string required_field = 1;" in proto
    assert "optional string optional_field = 2;" in proto
    assert "optional int32 optional_int = 3;" in proto


def test_optional_with_default_none():
    """Test optional fields with explicit None default."""

    class OptionalWithDefaultMessage(Message):
        name: str
        description: Optional[str] = None
        count: Optional[int] = None

    # Test proto generation using a dummy service
    class DummyService:
        def test_method(
            self, req: OptionalWithDefaultMessage
        ) -> OptionalWithDefaultMessage:
            return req

    proto = generate_proto(DummyService())
    assert "string name = 1;" in proto
    assert "optional string description = 2;" in proto
    assert "optional int32 count = 3;" in proto


def test_enum_types():
    """Test message with enum types."""

    class EnumMessage(Message):
        color: Color
        optional_color: Optional[Color]

    # Test proto generation using a dummy service
    class DummyService:
        def test_method(self, req: EnumMessage) -> EnumMessage:
            return req

    proto = generate_proto(DummyService())
    print(proto)
    assert "enum Color {" in proto
    assert "RED = 0;" in proto
    assert "GREEN = 1;" in proto
    assert "BLUE = 2;" in proto
    assert "Color color = 1;" in proto
    assert "optional Color optional_color = 2;" in proto


def test_nested_message():
    """Test message with nested message types."""

    class InnerMessage(Message):
        value: str
        optional_number: Optional[int]

    class OuterMessage(Message):
        name: str
        inner: InnerMessage
        optional_inner: Optional[InnerMessage]

    # Test proto generation using a dummy service
    class DummyService:
        def test_method(self, req: OuterMessage) -> OuterMessage:
            return req

    proto = generate_proto(DummyService())
    assert "message InnerMessage {" in proto
    assert "message OuterMessage {" in proto
    assert "string value = 1;" in proto
    assert "optional int32 optional_number = 2;" in proto
    assert "string name = 1;" in proto
    assert "InnerMessage inner = 2;" in proto
    assert "optional InnerMessage optional_inner = 3;" in proto


def test_complex_nested_with_unions():
    """Test complex nested message with unions and optionals."""

    class Address(Message):
        street: str
        city: str
        zipcode: Optional[str]

    class Contact(Message):
        email: Optional[str]
        phone: Optional[str]

    class Person(Message):
        name: str
        age: int
        address: Optional[Address]
        contact: Contact
        status: Union[str, int]
        metadata: Optional[Union[str, int]]

    # Test proto generation using a dummy service
    class DummyService:
        def test_method(self, req: Person) -> Person:
            return req

    proto = generate_proto(DummyService())
    assert "message Address {" in proto
    assert "message Contact {" in proto
    assert "message Person {" in proto
    assert "oneof status {" in proto
    assert "oneof metadata {" in proto


@pytest.mark.skipif(is_skip_generation(), reason="Skipping generation tests")
def test_bidirectional_conversion_primitive(request: FixtureRequest):
    """Test bidirectional conversion for primitive types."""

    class PrimitiveMessage(Message):
        text: str
        number: int
        flag: bool

    # Create dummy service for proto generation
    class PrimitiveDummyService:
        def test_method(self, req: PrimitiveMessage) -> PrimitiveMessage:
            return req

    # Generate proto and modules
    _, pb2_module = generate_and_compile_proto(
        PrimitiveDummyService(), request.node.unique_package_name
    )

    # Create Python message
    py_msg = PrimitiveMessage(text="hello", number=42, flag=True)

    # Convert to proto
    proto_msg = convert_python_message_to_proto(py_msg, PrimitiveMessage, pb2_module)
    assert getattr(proto_msg, "text", None) == "hello"
    assert getattr(proto_msg, "number", None) == 42
    assert getattr(proto_msg, "flag", None) is True

    # Convert back to Python
    converter = generate_message_converter(PrimitiveMessage)
    py_msg_back = converter(proto_msg)
    assert getattr(py_msg_back, "text", None) == "hello"
    assert getattr(py_msg_back, "number", None) == 42
    assert getattr(py_msg_back, "flag", None) is True


@pytest.mark.skipif(is_skip_generation(), reason="Skipping generation tests")
def test_bidirectional_conversion_optional(request: FixtureRequest):
    """Test bidirectional conversion for optional types."""

    class OptionalMessage(Message):
        name: str
        description: Optional[str] = None
        count: Optional[int] = None

    # Create dummy service for proto generation
    class OptionalDummyService:
        def test_method(self, req: OptionalMessage) -> OptionalMessage:
            return req

    # Generate proto and modules
    _, pb2_module = generate_and_compile_proto(
        OptionalDummyService(), request.node.unique_package_name
    )

    # Test with optional field set
    py_msg1 = OptionalMessage(name="test", description="desc", count=5)
    proto_msg1 = convert_python_message_to_proto(py_msg1, OptionalMessage, pb2_module)
    converter = generate_message_converter(OptionalMessage)
    py_msg1_back = converter(proto_msg1)
    assert getattr(py_msg1_back, "name", None) == "test", (
        f"py_msg1_back.name exists: {hasattr(py_msg1_back, 'name')}, value: {getattr(py_msg1_back, 'name', None)}, expected: test"
    )
    assert getattr(py_msg1_back, "description", None) == "desc", (
        f"py_msg1_back.description exists: {hasattr(py_msg1_back, 'description')}, value: {getattr(py_msg1_back, 'description', None)}, expected: desc"
    )
    assert getattr(py_msg1_back, "count", None) == 5, (
        f"py_msg1_back.count exists: {hasattr(py_msg1_back, 'count')}, value: {getattr(py_msg1_back, 'count', None)}, expected: 5"
    )

    # Test with optional field None
    py_msg2 = OptionalMessage(name="test2", description=None)
    proto_msg2 = convert_python_message_to_proto(py_msg2, OptionalMessage, pb2_module)
    py_msg2_back = converter(proto_msg2)
    assert getattr(py_msg2_back, "name", None) == "test2", (
        f"py_msg2_back.name exists: {hasattr(py_msg2_back, 'name')}, value: {getattr(py_msg2_back, 'name', None)}, expected: test2"
    )
    assert getattr(py_msg2_back, "description", None) is None, (
        f"py_msg2_back.description exists: {hasattr(py_msg2_back, 'description')}, value: {getattr(py_msg2_back, 'description', None)}, expected: None"
    )
    assert getattr(py_msg2_back, "count", None) is None, (
        f"py_msg2_back.count exists: {hasattr(py_msg2_back, 'count')}, value: {getattr(py_msg2_back, 'count', None)}, expected: None"
    )


@pytest.mark.skipif(is_skip_generation(), reason="Skipping generation tests")
def test_bidirectional_conversion_union(request: FixtureRequest):
    """Test bidirectional conversion for union types (oneof)."""

    class UnionMessage(Message):
        name: str
        value: Union[str, int]

    # Create dummy service for proto generation
    class UnionDummyService:
        def test_method(self, req: UnionMessage) -> UnionMessage:
            return req

    # Generate proto and modules
    _, pb2_module = generate_and_compile_proto(
        UnionDummyService(), request.node.unique_package_name
    )

    # Test with string value
    py_msg1 = UnionMessage(name="test", value="hello")
    proto_msg1 = convert_python_message_to_proto(py_msg1, UnionMessage, pb2_module)
    converter = generate_message_converter(UnionMessage)
    py_msg1_back = converter(proto_msg1)
    assert getattr(py_msg1_back, "name", None) == "test", (
        f"py_msg1_back.name exists: {hasattr(py_msg1_back, 'name')}, value: {getattr(py_msg1_back, 'name', None)}, expected: test"
    )
    assert getattr(py_msg1_back, "value", None) == "hello", (
        f"py_msg1_back.value exists: {hasattr(py_msg1_back, 'value')}, value: {getattr(py_msg1_back, 'value', None)}, expected: hello"
    )

    # Test with int value
    py_msg2 = UnionMessage(name="test", value=42)
    proto_msg2 = convert_python_message_to_proto(py_msg2, UnionMessage, pb2_module)
    py_msg2_back = converter(proto_msg2)
    assert getattr(py_msg2_back, "name", None) == "test", (
        f"py_msg2_back.name exists: {hasattr(py_msg2_back, 'name')}, value: {getattr(py_msg2_back, 'name', None)}, expected: test"
    )
    assert getattr(py_msg2_back, "value", None) == 42, (
        f"py_msg2_back.value exists: {hasattr(py_msg2_back, 'value')}, value: {getattr(py_msg2_back, 'value', None)}, expected: 42"
    )
    assert isinstance(getattr(py_msg2_back, "value", None), int), (
        f"py_msg2_back.value exists: {hasattr(py_msg2_back, 'value')}, value: {getattr(py_msg2_back, 'value', None)}, expected: int"
    )


@pytest.mark.skipif(is_skip_generation(), reason="Skipping generation tests")
def test_bidirectional_conversion_nested(request: FixtureRequest):
    """Test bidirectional conversion for nested messages."""

    class InnerMessage(Message):
        value: str
        optional_number: Optional[int]

    class OuterMessage(Message):
        name: str
        inner: InnerMessage
        optional_inner: Optional[InnerMessage]

    # Create dummy service for proto generation
    class NestedDummyService:
        def test_method(self, req: OuterMessage) -> OuterMessage:
            return req

    # Generate proto and modules
    _, pb2_module = generate_and_compile_proto(
        NestedDummyService(), request.node.unique_package_name
    )

    # Test with nested message
    inner = InnerMessage(value="inner_value", optional_number=10)
    py_msg = OuterMessage(name="outer", inner=inner, optional_inner=None)

    proto_msg = convert_python_message_to_proto(py_msg, OuterMessage, pb2_module)
    converter = generate_message_converter(OuterMessage)
    py_msg_back = converter(proto_msg)

    assert getattr(py_msg_back, "name", None) == "outer", (
        f"py_msg_back.name exists: {hasattr(py_msg_back, 'name')}, value: {getattr(py_msg_back, 'name', None)}, expected: outer"
    )
    assert (
        getattr(getattr(py_msg_back, "inner", None), "value", None) == "inner_value"
    ), (
        f"py_msg_back.inner.value exists: {hasattr(getattr(py_msg_back, 'inner', None), 'value')}, value: {getattr(getattr(py_msg_back, 'inner', None), 'value', None)}, expected: inner_value"
    )
    assert (
        getattr(getattr(py_msg_back, "inner", None), "optional_number", None) == 10
    ), (
        f"py_msg_back.inner.optional_number exists: {hasattr(getattr(py_msg_back, 'inner', None), 'optional_number')}, value: {getattr(getattr(py_msg_back, 'inner', None), 'optional_number', None)}, expected: 10"
    )
    assert getattr(py_msg_back, "optional_inner", None) is None, (
        f"py_msg_back.optional_inner exists: {hasattr(py_msg_back, 'optional_inner')}, value: {getattr(py_msg_back, 'optional_inner', None)}, expected: None"
    )


@pytest.mark.skipif(is_skip_generation(), reason="Skipping generation tests")
def test_bidirectional_conversion_enum(request: FixtureRequest):
    """Test bidirectional conversion for enum types."""

    class EnumMessage(Message):
        color: Color
        optional_color: Optional[Color] = None

    # Create dummy service for proto generation
    class EnumDummyService:
        def test_method(self, req: EnumMessage) -> EnumMessage:
            return req

    # Generate proto and modules
    _, pb2_module = generate_and_compile_proto(
        EnumDummyService(), request.node.unique_package_name
    )

    # Test with enum
    py_msg = EnumMessage(color=Color.RED, optional_color=Color.BLUE)
    proto_msg = convert_python_message_to_proto(py_msg, EnumMessage, pb2_module)
    converter = generate_message_converter(EnumMessage)
    py_msg_back = converter(proto_msg)

    assert getattr(py_msg_back, "color", None) == Color.RED, (
        f"py_msg_back.color exists: {hasattr(py_msg_back, 'color')}, value: {getattr(py_msg_back, 'color', None)}, expected: Color.RED"
    )
    assert getattr(py_msg_back, "optional_color", None) == Color.BLUE, (
        f"py_msg_back.optional_color exists: {hasattr(py_msg_back, 'optional_color')}, value: {getattr(py_msg_back, 'optional_color', None)}, expected: Color.BLUE"
    )

    # Test with None optional enum
    py_msg2 = EnumMessage(color=Color.GREEN)
    proto_msg2 = convert_python_message_to_proto(py_msg2, EnumMessage, pb2_module)
    py_msg2_back = converter(proto_msg2)

    assert getattr(py_msg2_back, "color", None) == Color.GREEN, (
        f"py_msg2_back.color exists: {hasattr(py_msg2_back, 'color')}, value: {getattr(py_msg2_back, 'color', None)}, expected: Color.GREEN"
    )
    assert getattr(py_msg2_back, "optional_color", None) is None, (
        f"py_msg2_back.optional_color exists: {hasattr(py_msg2_back, 'optional_color')}, value: {getattr(py_msg2_back, 'optional_color', None)}, expected: None"
    )


def test_invalid_message_no_annotation():
    """Test that message with fields without annotations fails."""

    class InvalidService:
        def test_method(self, req: Any) -> str:  # Missing proper annotation
            _ = req
            return "test"

    with pytest.raises(Exception):
        _ = generate_proto(InvalidService())


def test_validation_error_handling():
    """Test proper validation error handling."""

    class ValidatedMessage(Message):
        name: str
        age: int

    # This should work
    msg = ValidatedMessage(name="test", age=25)
    assert getattr(msg, "name", None) == "test", (
        f"msg.name exists: {hasattr(msg, 'name')}, value: {getattr(msg, 'name', None)}, expected: test"
    )
    assert getattr(msg, "age", None) == 25, (
        f"msg.age exists: {hasattr(msg, 'age')}, value: {getattr(msg, 'age', None)}, expected: 25"
    )

    # This should raise ValidationError
    with pytest.raises(ValidationError):
        _ = ValidatedMessage(name="test", age="not_a_number")  # pyright: ignore[reportArgumentType]


def test_list_and_dict_types():
    """Test message with list and dict types."""

    class CollectionMessage(Message):
        tags: list[str]
        scores: dict[str, int]
        optional_list: Optional[list[int]]

    # Create dummy service for proto generation
    class DummyService:
        def test_method(self, req: CollectionMessage) -> CollectionMessage:
            return req

    # Test proto generation
    proto = generate_proto(DummyService())
    assert "repeated string tags = 1;" in proto
    assert "map<string, int32> scores = 2;" in proto
    assert "optional repeated int32 optional_list = 3;" in proto


@pytest.mark.skipif(is_skip_generation(), reason="Skipping generation tests")
def test_bidirectional_conversion_collections(request: FixtureRequest):
    """Test bidirectional conversion for collections."""

    class CollectionMessage(Message):
        tags: list[str]
        scores: dict[str, int]

    # Create dummy service for proto generation
    class CollectionDummyService:
        def test_method(self, req: CollectionMessage) -> CollectionMessage:
            return req

    # Generate proto and modules
    _, pb2_module = generate_and_compile_proto(
        CollectionDummyService(), request.node.unique_package_name
    )

    # Test with collections
    py_msg = CollectionMessage(
        tags=["tag1", "tag2", "tag3"], scores={"a": 1, "b": 2, "c": 3}
    )

    proto_msg = convert_python_message_to_proto(py_msg, CollectionMessage, pb2_module)
    converter = generate_message_converter(CollectionMessage)
    py_msg_back = converter(proto_msg)

    assert getattr(py_msg_back, "tags", None) == ["tag1", "tag2", "tag3"], (
        f"py_msg_back.tags exists: {hasattr(py_msg_back, 'tags')}, value: {getattr(py_msg_back, 'tags', None)}, expected: ['tag1', 'tag2', 'tag3']"
    )
    assert getattr(py_msg_back, "scores", None) == {"a": 1, "b": 2, "c": 3}, (
        f"py_msg_back.scores exists: {hasattr(py_msg_back, 'scores')}, value: {getattr(py_msg_back, 'scores', None)}, expected: {'a': 1, 'b': 2, 'c': 3}"
    )


def test_reserved_fields_default():
    """Test that no reserved fields are added by default."""

    class SimpleMessage(Message):
        name: str
        value: int

    class DummyService:
        def test_method(self, req: SimpleMessage) -> SimpleMessage:
            return req

    # Test without setting environment variable
    proto = generate_proto(DummyService())
    assert "reserved" not in proto
    assert "Reserved fields" not in proto


def test_reserved_fields_single():
    """Test adding a single reserved field."""

    class SimpleMessage(Message):
        name: str
        value: int

    class DummyService:
        def test_method(self, req: SimpleMessage) -> SimpleMessage:
            return req

    # Test with 1 reserved field
    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": "1"}):
        proto = generate_proto(DummyService())
        assert "// Reserved fields for future compatibility" in proto
        assert "reserved 3;" in proto


def test_reserved_fields_multiple():
    """Test adding multiple reserved fields."""

    class SimpleMessage(Message):
        name: str
        value: int

    class DummyService:
        def test_method(self, req: SimpleMessage) -> SimpleMessage:
            return req

    # Test with 5 reserved fields
    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": "5"}):
        proto = generate_proto(DummyService())
        assert "// Reserved fields for future compatibility" in proto
        assert "reserved 3 to 7;" in proto


def test_reserved_fields_with_complex_message():
    """Test reserved fields with a more complex message containing unions and optionals."""

    class ComplexMessage(Message):
        name: str
        value: Union[str, int]
        optional_field: Optional[str]
        tags: list[str]

    class DummyService:
        def test_method(self, req: ComplexMessage) -> ComplexMessage:
            return req

    # Test with 3 reserved fields
    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": "3"}):
        proto = generate_proto(DummyService())
        assert "// Reserved fields for future compatibility" in proto
        # Complex message has: name=1, value oneof (2,3), optional_field=4, tags=5
        # So reserved should start at 6
        assert "reserved 6 to 8;" in proto


def test_reserved_fields_large_number():
    """Test adding a large number of reserved fields."""

    class SimpleMessage(Message):
        name: str

    class DummyService:
        def test_method(self, req: SimpleMessage) -> SimpleMessage:
            return req

    # Test with 50 reserved fields
    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": "50"}):
        proto = generate_proto(DummyService())
        assert "// Reserved fields for future compatibility" in proto
        assert "reserved 2 to 51;" in proto


def test_reserved_fields_zero():
    """Test that setting reserved fields to 0 doesn't add any."""

    class SimpleMessage(Message):
        name: str

    class DummyService:
        def test_method(self, req: SimpleMessage) -> SimpleMessage:
            return req

    # Test with 0 reserved fields
    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": "0"}):
        proto = generate_proto(DummyService())
        assert "reserved" not in proto
        assert "Reserved fields" not in proto


def test_reserved_fields_invalid_value():
    """Test that invalid values for reserved fields default to 0."""

    class SimpleMessage(Message):
        name: str

    class DummyService:
        def test_method(self, req: SimpleMessage) -> SimpleMessage:
            return req

    # Test with invalid string value
    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": "invalid"}):
        proto = generate_proto(DummyService())
        assert "reserved" not in proto
        assert "Reserved fields" not in proto

    # Test with negative value
    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": "-5"}):
        proto = generate_proto(DummyService())
        assert "reserved" not in proto
        assert "Reserved fields" not in proto


def test_reserved_fields_nested_messages():
    """Test that reserved fields are added to all message types in nested scenarios."""

    class InnerMessage(Message):
        value: str

    class OuterMessage(Message):
        name: str
        inner: InnerMessage

    class DummyService:
        def test_method(self, req: OuterMessage) -> OuterMessage:
            return req

    # Test with 2 reserved fields
    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": "2"}):
        proto = generate_proto(DummyService())

        # Should have reserved fields in both message types
        reserved_occurrences = proto.count(
            "// Reserved fields for future compatibility"
        )
        assert reserved_occurrences == 2

        # InnerMessage has value=1, so reserved should be 2 to 3
        assert "reserved 2 to 3;" in proto

        # OuterMessage has name=1, inner=2, so reserved should be 3 to 4
        assert "reserved 3 to 4;" in proto


def test_reserved_fields_with_enums():
    """Test reserved fields with messages containing enums."""

    class Status(enum.Enum):
        ACTIVE = 0
        INACTIVE = 1

    class MessageWithEnum(Message):
        name: str
        status: Status

    class DummyService:
        def test_method(self, req: MessageWithEnum) -> MessageWithEnum:
            return req

    # Test with 3 reserved fields
    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": "3"}):
        proto = generate_proto(DummyService())

        # Should have enum definition
        assert "enum Status {" in proto

        # Should have reserved fields in message
        assert "// Reserved fields for future compatibility" in proto
        # Message has name=1, status=2, so reserved should be 3 to 5
        assert "reserved 3 to 5;" in proto


@pytest.mark.skipif(is_skip_generation(), reason="Skipping generation tests")
def test_reserved_fields_compilation(request: FixtureRequest):
    """Test that proto files with reserved fields compile correctly."""

    class SimpleMessage(Message):
        name: str
        value: int

    class DummyService:
        def test_method(self, req: SimpleMessage) -> SimpleMessage:
            return req

    # Test with reserved fields - should compile without errors
    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": "5"}):
        try:
            pb2_grpc_module, pb2_module = generate_and_compile_proto(
                DummyService(), request.node.unique_package_name
            )
            # If we get here without exception, compilation was successful
            assert pb2_grpc_module is not None
            assert pb2_module is not None
        except Exception as e:
            pytest.fail(f"Proto compilation failed with reserved fields: {e}")


def test_get_reserved_fields_count_function():
    """Test the get_reserved_fields_count function directly."""
    from pydantic_rpc.core import get_reserved_fields_count

    # Test default (no env var)
    with mock.patch.dict(os.environ, {}, clear=True):
        assert get_reserved_fields_count() == 0

    # Test valid values
    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": "10"}):
        assert get_reserved_fields_count() == 10

    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": "1"}):
        assert get_reserved_fields_count() == 1

    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": "0"}):
        assert get_reserved_fields_count() == 0

    # Test invalid values
    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": "invalid"}):
        assert get_reserved_fields_count() == 0

    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": ""}):
        assert get_reserved_fields_count() == 0

    with mock.patch.dict(os.environ, {"PYDANTIC_RPC_RESERVED_FIELDS": "-5"}):
        assert get_reserved_fields_count() == 0
