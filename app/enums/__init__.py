from enum import Enum

class State(Enum):
    """ State of the agent which is either active, inactive, or unknown. """
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"

class Mode(Enum):
    """ Mode of the agent which is either enforcing or monitoring. """
    ENFORCING = "enforcing"
    MONITORING = "monitoring"

class Type(Enum):
    """ Type of the agent which is either host or container. """
    HOST = "host"
    NETWORK = "network"
    CONTAINER = "container"
    UNKNOWN = "unknown"
    
    
    