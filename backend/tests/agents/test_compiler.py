"""
Tests for Compiler

The Compiler transforms Spec → IR, filling in defaults and generating IDs.
"""
import pytest
from agents.core.compiler import Compiler
from agents.schemas import ModSpec, ItemSpec, Rarity, CreativeTab


class TestCompiler:
    """Test suite for Compiler"""

    @pytest.fixture
    def compiler(self):
        """Create compiler instance"""
        return Compiler()

    @pytest.fixture
    def simple_spec(self):
        """Create a simple mod spec for testing"""
        return ModSpec(
            mod_name="Test Mod",
            mod_id="test_mod",
            version="1.0.0",
            author="Tester",
            description="A test mod",
            items=[
                ItemSpec(
                    item_name="Test Item",
                    item_id="test_item",
                    description="A test item",
                    rarity=Rarity.COMMON,
                    creative_tab=CreativeTab.MISC
                )
            ],
            blocks=[],
            tools=[]
        )

    def test_compiler_initialization(self, compiler):
        """Test that compiler initializes correctly"""
        assert compiler is not None

    def test_compile_simple_spec(self, compiler, simple_spec):
        """Test compiling a simple spec to IR"""
        ir = compiler.compile(simple_spec)

        # Check basic fields
        assert ir.mod_id == "test_mod"
        assert ir.mod_name == "Test Mod"
        assert ir.version == "1.0.0"
        assert ir.author == "Tester"

        # Check that defaults are filled
        assert ir.minecraft_version is not None
        assert ir.fabric_loader_version is not None
        assert ir.base_package is not None
        assert ir.main_class_name is not None

        # Check items
        assert len(ir.items) == 1
        item = ir.items[0]
        assert item.item_id == "test_mod:test_item"
        assert item.display_name == "Test Item"

        # Check that item has required fields
        assert item.max_stack_size > 0
        assert item.rarity is not None
        assert item.fireproof is not None

    def test_compiler_generates_registry_ids(self, compiler, simple_spec):
        """Test that compiler generates proper registry IDs"""
        ir = compiler.compile(simple_spec)

        for item in ir.items:
            # Check namespace:path format
            assert ":" in item.item_id
            namespace, path = item.item_id.split(":")
            assert namespace == ir.mod_id

    def test_compiler_generates_package_names(self, compiler, simple_spec):
        """Test that compiler generates valid package names"""
        ir = compiler.compile(simple_spec)

        # Check package format
        assert ir.base_package.startswith("com.example.")
        assert "." in ir.base_package

        # Check main class name
        assert ir.main_class_name[0].isupper()
        assert " " not in ir.main_class_name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
