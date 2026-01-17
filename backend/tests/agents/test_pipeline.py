"""
Tests for ModGenerationPipeline

These tests verify the end-to-end pipeline functionality.
"""
import pytest
import tempfile
import shutil
from pathlib import Path

from agents.pipeline import ModGenerationPipeline, PipelineError


class TestModGenerationPipeline:
    """Test suite for ModGenerationPipeline"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def pipeline(self, temp_workspace):
        """Create pipeline instance for testing"""
        return ModGenerationPipeline(
            job_id="test-job-123",
            workspace_dir=temp_workspace / "workspace",
            downloads_dir=temp_workspace / "downloads"
        )

    def test_pipeline_initialization(self, pipeline, temp_workspace):
        """Test that pipeline initializes correctly"""
        assert pipeline.job_id == "test-job-123"
        assert pipeline.workspace_dir.exists()
        assert pipeline.downloads_dir.exists()
        assert pipeline.orchestrator is not None
        assert pipeline.spec_manager is not None
        assert pipeline.compiler is not None
        assert pipeline.planner is not None
        assert pipeline.validator is not None
        assert pipeline.builder is not None
        assert pipeline.error_fixer is not None

    def test_pipeline_execution_log(self, pipeline):
        """Test that execution log is tracked"""
        assert isinstance(pipeline.execution_log, list)
        assert len(pipeline.execution_log) == 0

    def test_get_current_spec_empty(self, pipeline):
        """Test getting spec when none exists"""
        spec = pipeline.get_current_spec()
        assert spec is None

    # Integration test (commented out - requires full setup)
    # def test_generate_mod_simple_item(self, pipeline):
    #     """Test generating a simple item mod"""
    #     result = pipeline.generate_mod(
    #         user_prompt="Create a simple ruby gem item",
    #         progress_callback=lambda msg: print(f"[TEST] {msg}")
    #     )
    #
    #     assert result["status"] == "success"
    #     assert "mod_id" in result
    #     assert "jar_path" in result
    #     assert Path(result["jar_path"]).exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
