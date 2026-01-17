"""
Tests for Tools

Test individual tool implementations.
"""
import pytest
import tempfile
import shutil
from pathlib import Path

from agents.tools import (
    setup_workspace,
    generate_gradle_files,
    generate_fabric_mod_json,
    create_tool_registry
)


class TestWorkspaceTool:
    """Test workspace setup tool"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp = Path(tempfile.mkdtemp())
        yield temp
        if temp.exists():
            shutil.rmtree(temp)

    def test_setup_workspace(self, temp_dir):
        """Test creating workspace structure"""
        result = setup_workspace(
            workspace_dir=temp_dir,
            mod_id="test_mod",
            package_name="com.example.testmod"
        )

        assert result["status"] == "success"
        assert Path(result["workspace_path"]).exists()

        # Check that key directories were created
        workspace = Path(result["workspace_path"])
        assert (workspace / "src" / "main" / "java").exists()
        assert (workspace / "src" / "main" / "resources").exists()


class TestGradleTool:
    """Test Gradle file generation tool"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp = Path(tempfile.mkdtemp())
        yield temp
        if temp.exists():
            shutil.rmtree(temp)

    def test_generate_gradle_files(self, temp_dir):
        """Test generating Gradle build files"""
        result = generate_gradle_files(
            workspace_path=temp_dir,
            mod_id="test_mod",
            mod_name="Test Mod",
            version="1.0.0"
        )

        assert result["status"] == "success"
        assert Path(result["build_gradle_path"]).exists()
        assert Path(result["settings_gradle_path"]).exists()
        assert Path(result["gradle_properties_path"]).exists()

        # Check content
        build_gradle = Path(result["build_gradle_path"]).read_text()
        assert "fabric-loom" in build_gradle


class TestFabricJsonTool:
    """Test fabric.mod.json generation tool"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp = Path(tempfile.mkdtemp())
        yield temp
        if temp.exists():
            shutil.rmtree(temp)

    def test_generate_fabric_mod_json(self, temp_dir):
        """Test generating fabric.mod.json"""
        # Create resources directory
        resources_dir = temp_dir / "src" / "main" / "resources"
        resources_dir.mkdir(parents=True)

        result = generate_fabric_mod_json(
            workspace_path=temp_dir,
            mod_id="test_mod",
            mod_name="Test Mod",
            version="1.0.0",
            description="A test mod",
            authors=["Tester"]
        )

        assert result["status"] == "success"
        assert Path(result["fabric_mod_json_path"]).exists()

        # Check content
        import json
        fabric_json = json.loads(Path(result["fabric_mod_json_path"]).read_text())
        assert fabric_json["id"] == "test_mod"
        assert fabric_json["name"] == "Test Mod"


class TestToolRegistry:
    """Test tool registry"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp = Path(tempfile.mkdtemp())
        yield temp
        if temp.exists():
            shutil.rmtree(temp)

    def test_create_tool_registry(self, temp_dir):
        """Test creating tool registry"""
        registry = create_tool_registry(temp_dir)

        assert isinstance(registry, dict)
        assert len(registry) > 0

        # Check that expected tools are registered
        assert "setup_workspace" in registry
        assert "generate_gradle_files" in registry
        assert "generate_fabric_mod_json" in registry
        assert "generate_java_code" in registry
        assert "generate_assets" in registry

    def test_tool_callable(self, temp_dir):
        """Test that registered tools are callable"""
        registry = create_tool_registry(temp_dir)

        # Check that tools are callable
        for tool_name, tool_func in registry.items():
            assert callable(tool_func)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
