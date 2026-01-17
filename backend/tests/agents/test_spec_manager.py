"""
Tests for SpecManager

The SpecManager maintains the canonical mod specification with versioning.
"""
import pytest
import tempfile
import shutil
from pathlib import Path

from agents.core.spec_manager import SpecManager
from agents.schemas import ModSpec, SpecDelta, ItemSpec, Rarity, CreativeTab


class TestSpecManager:
    """Test suite for SpecManager"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for specs"""
        temp = Path(tempfile.mkdtemp())
        yield temp
        if temp.exists():
            shutil.rmtree(temp)

    @pytest.fixture
    def spec_manager(self, temp_dir):
        """Create SpecManager instance"""
        return SpecManager(spec_dir=temp_dir)

    @pytest.fixture
    def sample_delta(self):
        """Create a sample spec delta"""
        return SpecDelta(
            delta_type="create",
            mod_name="Test Mod",
            mod_id="test_mod",
            version="1.0.0",
            author="Tester",
            description="A test mod",
            items_to_add=[
                ItemSpec(
                    item_name="Ruby",
                    item_id="ruby",
                    description="A shiny ruby gem",
                    rarity=Rarity.RARE,
                    creative_tab=CreativeTab.MISC
                )
            ]
        )

    def test_spec_manager_initialization(self, spec_manager, temp_dir):
        """Test that SpecManager initializes correctly"""
        assert spec_manager.spec_dir == temp_dir
        assert spec_manager.spec_file.name == "mod_spec.json"
        assert spec_manager.history_dir.name == "history"

    def test_get_current_spec_none(self, spec_manager):
        """Test getting spec when none exists"""
        spec = spec_manager.get_current_spec()
        assert spec is None

    def test_apply_create_delta(self, spec_manager, sample_delta):
        """Test applying a create delta"""
        spec = spec_manager.apply_delta(sample_delta)

        assert spec is not None
        assert spec.mod_name == "Test Mod"
        assert spec.mod_id == "test_mod"
        assert len(spec.items) == 1
        assert spec.items[0].item_name == "Ruby"

    def test_spec_persistence(self, spec_manager, sample_delta):
        """Test that specs are persisted to disk"""
        spec_manager.apply_delta(sample_delta)

        # Create new manager instance
        new_manager = SpecManager(spec_dir=spec_manager.spec_dir)
        loaded_spec = new_manager.get_current_spec()

        assert loaded_spec is not None
        assert loaded_spec.mod_name == "Test Mod"
        assert len(loaded_spec.items) == 1

    def test_spec_versioning(self, spec_manager, sample_delta):
        """Test that spec versions are tracked"""
        # Apply first delta
        spec1 = spec_manager.apply_delta(sample_delta)
        version1 = spec1.version

        # Apply another delta
        update_delta = SpecDelta(
            delta_type="update",
            items_to_add=[
                ItemSpec(
                    item_name="Emerald",
                    item_id="emerald",
                    description="A green emerald",
                    rarity=Rarity.RARE,
                    creative_tab=CreativeTab.MISC
                )
            ]
        )
        spec2 = spec_manager.apply_delta(update_delta)
        version2 = spec2.version

        # Versions should be different
        assert version1 != version2
        assert len(spec2.items) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
