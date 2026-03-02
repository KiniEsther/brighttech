"""
Application configuration settings
"""
import os


class Config:
    """Base configuration"""
    DEBUG = False
    TESTING = False
    
    # Server settings
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    
    # Elevator settings
    DEFAULT_FLOORS = 10
    DEFAULT_ELEVATORS = 2
    MAX_CAPACITY = 1000  # kg
    MAX_PASSENGERS = 8
    
    # Timing settings (in seconds)
    FLOOR_TRAVEL_TIME = 2.0
    DOOR_OPEN_TIME = 1.5
    DOOR_CLOSE_TIME = 1.5
    DOOR_TIMEOUT = 5.0
    
    # Safety settings
    EMERGENCY_STOP_ENABLED = True
    OVERLOAD_CHECK_ENABLED = True


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEFAULT_FLOORS = 5
    DEFAULT_ELEVATORS = 1


def get_config(env=None):
    """
    Get configuration based on environment
    
    Args:
        env: Environment name (development, production, testing)
        
    Returns:
        Configuration object
    """
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    return configs.get(env, DevelopmentConfig)
