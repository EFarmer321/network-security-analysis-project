from constants import * 

def is_port_in_valid_range(port):
    return port >= PORT_RANGE_MIN and port <= PORT_RANGE_MAX

def lerp(a, b, t): 
    return a + (b - a) * t