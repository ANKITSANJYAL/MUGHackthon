"""
Test for logger utility
"""
import logging
from utils.logger import setup_logger

def test_logger_default_level():
    """Test that logger default level is DEBUG"""
    logger = setup_logger('test_logger')
    
    # Should be DEBUG (10), not INFO (20)
    assert logger.level == logging.DEBUG, \
        f"Expected DEBUG level (10), got {logger.level}"

def test_logger_custom_level():
    """Test that logger accepts custom level"""
    logger = setup_logger('test_logger', level='WARNING')
    assert logger.level == logging.WARNING
