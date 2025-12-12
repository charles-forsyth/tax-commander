import pytest
import os
import sys
import shutil
from tax_commander.db_manager import DBManager

# Ensure src is in path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

@pytest.fixture
def temp_env(tmp_path):
    """
    Creates a temporary environment for running tests.
    Sets CWD to the temp path so generated files (bills, reports) go there.
    """
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    # Copy schema.sql if needed, or rely on bundle logic
    # We might need config.yaml or we can rely on defaults
    
    yield tmp_path
    
    os.chdir(old_cwd)

@pytest.fixture
def db(temp_env):
    """
    Initializes a fresh database in the temp environment.
    """
    db_file = "test_tioga_tax.db"
    # We need to locate the schema. Since we are installed/local, 
    # we can try to find it in the original source or let DBManager find it via bundle.
    
    # Let's assume the bundle logic works, or explicitly point to source schema
    source_schema = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/tax_commander/schema.sql'))
    
    manager = DBManager(db_path=db_file, schema_path=source_schema)
    return manager
