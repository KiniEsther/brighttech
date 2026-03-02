"""
Data models for the elevator management system
"""
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
import uuid


class ElevatorState(Enum):
    """Elevator operational states"""
    IDLE = "idle"
    MOVING_UP = "moving_up"
    MOVING_DOWN = "moving_down"
    DOORS_OPENING = "doors_opening"
    DOORS_OPEN = "doors_open"
    DOORS_CLOSING = "doors_closing"
    EMERGENCY_STOP = "emergency_stop"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"


class Direction(Enum):
    """Elevator movement direction"""
    UP = "up"
    DOWN = "down"
    NONE = "none"


class RequestStatus(Enum):
    """Status of floor requests"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Floor:
    """Represents a floor in the building"""
    number: int
    name: str = ""
    has_elevator_access: bool = True
    
    def __post_init__(self):
        if not self.name:
            self.name = f"Floor {self.number}"


@dataclass
class ElevatorRequest:
    """Represents a floor request"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    floor: int = 0
    target_floor: int = 0
    direction: Direction = Direction.NONE
    status: RequestStatus = RequestStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    assigned_elevator_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    passenger_count: int = 1
    is_emergency: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'floor': self.floor,
            'target_floor': self.target_floor,
            'direction': self.direction.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'assigned_elevator_id': self.assigned_elevator_id,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'passenger_count': self.passenger_count,
            'is_emergency': self.is_emergency
        }


@dataclass
class Elevator:
    """Represents an elevator in the building"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Elevator"
    current_floor: int = 0
    target_floor: int = 0
    state: ElevatorState = ElevatorState.IDLE
    direction: Direction = Direction.NONE
    capacity: int = 8  # max passengers
    current_load: int = 0  # current passengers
    max_weight: int = 1000  # kg
    current_weight: int = 0  # kg
    floors: List[int] = field(default_factory=list)
    requests: List[str] = field(default_factory=list)  # request IDs
    door_open: bool = False
    is_operational: bool = True
    is_in_emergency: bool = False
    last_maintenance: Optional[datetime] = None
    total_trips: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'current_floor': self.current_floor,
            'target_floor': self.target_floor,
            'state': self.state.value,
            'direction': self.direction.value,
            'capacity': self.capacity,
            'current_load': self.current_load,
            'max_weight': self.max_weight,
            'current_weight': self.current_weight,
            'floors': self.floors,
            'requests': self.requests,
            'door_open': self.door_open,
            'is_operational': self.is_operational,
            'is_in_emergency': self.is_in_emergency,
            'last_maintenance': self.last_maintenance.isoformat() if self.last_maintenance else None,
            'total_trips': self.total_trips
        }
    
    def can_accept_request(self, passenger_count: int = 1) -> bool:
        """Check if elevator can accept a new request"""
        return (
            self.is_operational and 
            not self.is_in_emergency and 
            self.current_load + passenger_count <= self.capacity
        )
    
    def is_available(self) -> bool:
        """Check if elevator is available for new requests"""
        return (
            self.state == ElevatorState.IDLE and
            self.is_operational and 
            not self.is_in_emergency and
            not self.door_open
        )


@dataclass
class Building:
    """Represents a building with elevators"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Building"
    address: str = ""
    floors: List[Floor] = field(default_factory=list)
    elevators: List[Elevator] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self, include_elevators: bool = True) -> dict:
        """Convert to dictionary"""
        result = {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'floors': [f.__dict__ for f in self.floors],
            'floor_count': len(self.floors),
            'elevator_count': len(self.elevators),
            'created_at': self.created_at.isoformat()
        }
        
        if include_elevators:
            result['elevators'] = [e.to_dict() for e in self.elevators]
            
        return result
    
    def get_elevator(self, elevator_id: str) -> Optional[Elevator]:
        """Get elevator by ID"""
        for elevator in self.elevators:
            if elevator.id == elevator_id:
                return elevator
        return None
    
    def get_available_elevator(self) -> Optional[Elevator]:
        """Get first available elevator"""
        for elevator in self.elevators:
            if elevator.is_available():
                return elevator
        return None


class BuildingManager:
    """Manages buildings in the system"""
    
    def __init__(self):
        self._buildings: Dict[str, Building] = {}
    
    def create_building(
        self, 
        name: str, 
        floor_count: int = 10, 
        elevator_count: int = 2,
        address: str = ""
    ) -> Building:
        """
        Create a new building with elevators
        
        Args:
            name: Building name
            floor_count: Number of floors
            elevator_count: Number of elevators
            address: Building address
            
        Returns:
            Created building
        """
        building = Building(
            name=name,
            address=address
        )
        
        # Create floors (0 to floor_count-1)
        for i in range(floor_count):
            floor = Floor(number=i, name=f"Level {i}")
            building.floors.append(floor)
        
        # Create elevators
        for i in range(elevator_count):
            elevator = Elevator(
                name=f"Elevator {i + 1}",
                floors=list(range(floor_count))
            )
            building.elevators.append(elevator)
        
        self._buildings[building.id] = building
        return building
    
    def get_building(self, building_id: str) -> Optional[Building]:
        """Get building by ID"""
        return self._buildings.get(building_id)
    
    def get_all_buildings(self) -> List[Building]:
        """Get all buildings"""
        return list(self._buildings.values())
    
    def delete_building(self, building_id: str) -> bool:
        """Delete a building"""
        if building_id in self._buildings:
            del self._buildings[building_id]
            return True
        return False
