"""
Simple logging utility with intentional bug for testing
"""
import logging

def setup_logger(name, level='INFO'):
    """
    Setup a logger with the given name and level
    
    Bug: Log level should be 'DEBUG' by default, not 'INFO'
    This causes debug messages to be missed in production
    """
    logger = logging.getLogger(name)
    
    # BUG: Should be DEBUG for development environments
    log_level = getattr(logging, level.upper())
    logger.setLevel(log_level)
    
    # Add console handler
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
