from constants import * 

def is_port_in_valid_range(port: int):
    return port >= PORT_RANGE_MIN and port <= PORT_RANGE_MAX

def lerp(a: float, b: float, t: float): 
    return a + (b - a) * t

def clamp(value: float, min_value: float, max_value: float):
    return max(min_value, min(max_value, value))