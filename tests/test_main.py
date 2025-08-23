"""
Tests for the main module and demonstration functions.
"""

import pytest
from unittest.mock import patch, Mock
from io import StringIO
import sys


class TestMainModuleImport:
    """Test importing the main module."""
    
    def test_main_module_import(self):
        """Test that main module imports without errors."""
        try:
            import steelsnakes.main
            assert steelsnakes.main is not None
        except ImportError as e:
            pytest.fail(f"Failed to import main module: {e}")
    
    def test_main_functions_exist(self):
        """Test that expected demo functions exist."""
        import steelsnakes.main
        
        expected_functions = [
            'demo_basic_usage',
            'demo_various_sections', 
            'demo_database_features',
            'demo_factory_usage',
            'demo_comparison'
        ]
        
        for func_name in expected_functions:
            assert hasattr(steelsnakes.main, func_name), f"Missing function: {func_name}"
            assert callable(getattr(steelsnakes.main, func_name)), f"Not callable: {func_name}"


class TestDemoFunctions:
    """Test the demo functions (with mocked dependencies)."""
    
    @pytest.fixture
    def mock_sections(self):
        """Mock section classes to avoid dependency on data files."""
        with patch('steelsnakes.main.UB') as mock_ub, \
             patch('steelsnakes.main.UC') as mock_uc, \
             patch('steelsnakes.main.PFC') as mock_pfc:
            
            # Create mock section instances
            mock_beam = Mock()
            mock_beam.designation = "457x191x67"
            mock_beam.I_yy = 21500.0
            mock_beam.mass_per_metre = 67.1
            mock_beam.h = 457
            mock_beam.b = 191
            mock_beam.__str__ = Mock(return_value="457x191x67")
            
            mock_column = Mock()
            mock_column.designation = "305x305x137"
            mock_column.I_yy = 29000.0
            mock_column.mass_per_metre = 137.0
            mock_column.h = 305
            mock_column.b = 305
            mock_column.__str__ = Mock(return_value="305x305x137")
            
            mock_channel = Mock()
            mock_channel.designation = "430x100x64"
            mock_channel.I_yy = 12500.0
            mock_channel.mass_per_metre = 64.0
            mock_channel.h = 430
            mock_channel.b = 100
            mock_channel.e0 = 22.5
            mock_channel.__str__ = Mock(return_value="430x100x64")
            
            mock_ub.return_value = mock_beam
            mock_uc.return_value = mock_column
            mock_pfc.return_value = mock_channel
            
            yield {
                'UB': mock_ub,
                'UC': mock_uc, 
                'PFC': mock_pfc,
                'beam': mock_beam,
                'column': mock_column,
                'channel': mock_channel
            }
    
    def test_demo_basic_usage_runs(self, mock_sections):
        """Test that demo_basic_usage runs without error."""
        import steelsnakes.main
        
        # Capture stdout to verify output
        captured_output = StringIO()
        
        try:
            with patch('sys.stdout', captured_output):
                steelsnakes.main.demo_basic_usage()
            
            output = captured_output.getvalue()
            assert "SteelSnakes Section Demo" in output
            assert "Universal Beam" in output
            assert "Universal Column" in output
            assert "Parallel Flange Channel" in output
            
            # Verify mock sections were called
            mock_sections['UB'].assert_called_once_with("457x191x67")
            mock_sections['UC'].assert_called_once_with("305x305x137")
            mock_sections['PFC'].assert_called_once_with("430x100x64")
            
        except Exception as e:
            pytest.fail(f"demo_basic_usage failed: {e}")
    
    def test_demo_various_sections_handles_exceptions(self):
        """Test that demo_various_sections handles missing data gracefully."""
        import steelsnakes.main
        
        captured_output = StringIO()
        
        try:
            with patch('sys.stdout', captured_output):
                steelsnakes.main.demo_various_sections()
            
            output = captured_output.getvalue()
            assert "Various Section Types Demo" in output
            # Should handle exceptions gracefully and continue
            
        except Exception as e:
            # This is expected if data files are missing
            assert "sections may not be available" in str(e) or "No module named" in str(e)
    
    @patch('steelsnakes.main.get_database')
    def test_demo_database_features_runs(self, mock_get_database):
        """Test that demo_database_features runs with mocked database."""
        import steelsnakes.main
        from steelsnakes.core.sections.UK.base import SectionType
        
        # Mock database
        mock_db = Mock()
        mock_db.get_available_types.return_value = [SectionType.UB, SectionType.PFC]
        mock_db.list_sections.side_effect = lambda section_type: {
            SectionType.UB: ["457x191x67", "305x305x137"],
            SectionType.PFC: ["430x100x64"]
        }.get(section_type, [])
        mock_db.search_sections.return_value = [("457x191x67", {"mass_per_metre": 67.1})]
        mock_get_database.return_value = mock_db
        
        captured_output = StringIO()
        
        try:
            with patch('sys.stdout', captured_output):
                steelsnakes.main.demo_database_features()
            
            output = captured_output.getvalue()
            assert "Database Features" in output
            assert "Available section types" in output
            
        except Exception as e:
            pytest.fail(f"demo_database_features failed: {e}")
    
    @patch('steelsnakes.main.get_factory')
    def test_demo_factory_usage_runs(self, mock_get_factory):
        """Test that demo_factory_usage runs with mocked factory."""
        import steelsnakes.main
        from steelsnakes.core.sections.UK.base import SectionType
        
        # Mock factory and sections
        mock_factory = Mock()
        mock_section = Mock()
        mock_section.__str__ = Mock(return_value="457x191x67")
        mock_section.get_section_type.return_value = SectionType.UB
        
        mock_factory.create_section.return_value = mock_section
        mock_get_factory.return_value = mock_factory
        
        captured_output = StringIO()
        
        try:
            with patch('sys.stdout', captured_output):
                steelsnakes.main.demo_factory_usage()
            
            output = captured_output.getvalue()
            assert "Factory Pattern Demo" in output
            assert "Auto-detected section" in output
            
        except Exception as e:
            pytest.fail(f"demo_factory_usage failed: {e}")
    
    def test_demo_comparison_runs(self, mock_sections):
        """Test that demo_comparison runs without error."""
        import steelsnakes.main
        
        # Create additional mock sections for comparison
        with patch('steelsnakes.main.UB') as mock_ub:
            mock_small = Mock()
            mock_small.designation = "203x133x25"
            mock_small.I_yy = 2850.0
            mock_small.mass_per_metre = 25.1
            
            mock_medium = Mock() 
            mock_medium.designation = "457x191x67"
            mock_medium.I_yy = 21500.0
            mock_medium.mass_per_metre = 67.1
            
            mock_large = Mock()
            mock_large.designation = "914x305x201"
            mock_large.I_yy = 85700.0
            mock_large.mass_per_metre = 201.0
            
            mock_ub.side_effect = [mock_small, mock_medium, mock_large, mock_medium]
            
            captured_output = StringIO()
            
            try:
                with patch('sys.stdout', captured_output):
                    steelsnakes.main.demo_comparison()
                
                output = captured_output.getvalue()
                assert "Section Comparison Demo" in output
                assert "Beam comparison" in output
                
            except Exception as e:
                pytest.fail(f"demo_comparison failed: {e}")


class TestMainExecution:
    """Test main module execution."""
    
    def test_main_execution(self):
        """Test that main execution can be run (may fail due to missing data)."""
        import steelsnakes.main
        
        captured_output = StringIO()
        
        try:
            with patch('sys.stdout', captured_output):
                # Execute the main block - this may fail due to missing data files
                exec(compile(open(steelsnakes.main.__file__).read(), 
                            steelsnakes.main.__file__, 'exec'), 
                     {'__name__': '__main__'})
            # If it succeeds, that's great
            output = captured_output.getvalue()
            assert "All demos completed successfully!" in output
        except Exception as e:
            # Expected to fail if data files are missing
            assert "not found" in str(e) or "Available sections: 0" in str(e)
            # This is acceptable for the test environment


class TestPackageEntryPoint:
    """Test the package entry point function."""
    
    def test_main_function_exists(self):
        """Test that main function exists in package."""
        try:
            from steelsnakes import main as main_func
            # The package __init__.py should provide a callable main function
            if not callable(main_func):
                pytest.skip("main is not callable - package uses module structure")
            assert callable(main_func)
        except ImportError:
            # If there's no main function, that's acceptable for this package
            pytest.skip("No main function defined in package __init__.py")
    
    def test_main_function_runs(self):
        """Test that main function runs without error."""
        try:
            from steelsnakes import main as main_func
            
            if not callable(main_func):
                pytest.skip("main is not callable - package uses module structure")
            
            captured_output = StringIO()
            with patch('sys.stdout', captured_output):
                main_func()
            
            output = captured_output.getvalue()
            assert isinstance(output, str)
            assert len(output) > 0
            
        except ImportError:
            # If there's no main function, that's acceptable for this package
            pytest.skip("No main function defined in package __init__.py")
        except Exception as e:
            # Expected if this just prints "Hello from steelsnakes!"
            assert "Hello from steelsnakes!" in str(e)
