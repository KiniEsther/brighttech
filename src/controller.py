"""
Core elevator controller service
Handles elevator operations, state management, and movement
"""
import time
import threading
from typing import List, Optional, Dict, Callable
from datetime import datetime
from src.models import (
    Building, 
    Elevator, 
    ElevatorRequest, 
    ElevatorState, 
    Direction,
    RequestStatus,
    BuildingManager
)
from src.config import Config


class ElevatorController:
    """
    Core controller for managing elevator operations
    """
    
    def __init__(self, building: Building, config: Config = None):
        self.building = building
        self.config = config or Config()
        self.requests: Dict[str, ElevatorRequest] = {}
        self._lock = threading.RLock()
        self._simulation_running = False
        self._simulation_thread: Optional[threading.Thread] = None
        self._callbacks: Dict[str, List[Callable]] = {
            'state_changed': [],
            'request_completed': [],
            'emergency': []
        }
    
    def add_request(
        self, 
        floor: int, 
        target_floor: int,
        passenger_count: int = 1,
        is_emergency: bool = False
    ) -> ElevatorRequest:
        """
        Add a new floor request
        
        Args:
            floor: Current floor of the request
            target_floor: Destination floor
            passenger_count: Number of passengers
            is_emergency: Whether this is an emergency request
            
        Returns:
            Created request
        """
        with self._lock:
            # Validate floors
            if floor < 0 or floor >= len(self.building.floors):
                raise ValueError(f"Invalid floor: {floor}")
            if target_floor < 0 or target_floor >= len(self.building.floors):
                raise ValueError(f"Invalid target floor: {target_floor}")
            
            # Determine direction
            direction = Direction.NONE
            if target_floor > floor:
                direction = Direction.UP
            elif target_floor < floor:
                direction = Direction.DOWN
            
            # Create request
            request = ElevatorRequest(
                floor=floor,
                target_floor=target_floor,
                direction=direction,
                passenger_count=passenger_count,
                is_emergency=is_emergency
            )
            
            self.requests[request.id] = request
            return request
    
    def assign_request(self, request_id: str, elevator_id: str) -> bool:
        """
        Assign a request to an elevator
        
        Args:
            request_id: Request ID
            elevator_id: Elevator ID
            
        Returns:
            True if assignment successful
        """
        with self._lock:
            request = self.requests.get(request_id)
            if not request or request.status != RequestStatus.PENDING:
                return False
            
            elevator = self.building.get_elevator(elevator_id)
            if not elevator or not elevator.can_accept_request(request.passenger_count):
                return False
            
            # Assign request to elevator
            request.assigned_elevator_id = elevator_id
            request.status = RequestStatus.ASSIGNED
            elevator.requests.append(request_id)
            
            # Update elevator target if needed
            if elevator.state == ElevatorState.IDLE:
                elevator.target_floor = request.floor
            
            return True
    
    def start_elevator(self, elevator_id: str) -> bool:
        """
        Start elevator movement towards its target
        
        Args:
            elevator_id: Elevator ID
            
        Returns:
            True if started successfully
        """
        with self._lock:
            elevator = self.building.get_elevator(elevator_id)
            if not elevator or not elevator.is_operational:
                return False
            
            if elevator.state != ElevatorState.IDLE:
                return False
            
            # Determine direction
            if elevator.current_floor < elevator.target_floor:
                elevator.direction = Direction.UP
                elevator.state = ElevatorState.MOVING_UP
            elif elevator.current_floor > elevator.target_floor:
                elevator.direction = Direction.DOWN
                elevator.state = ElevatorState.MOVING_DOWN
            else:
                # Already at target
                self._open_doors(elevator)
                return True
            
            return True
    
    def _open_doors(self, elevator: Elevator) -> None:
        """Open elevator doors"""
        elevator.state = ElevatorState.DOORS_OPENING
        self._notify_callbacks('state_changed', elevator)
        
        # Simulate door opening time
        time.sleep(self.config.DOOR_OPEN_TIME)
        
        elevator.state = ElevatorState.DOORS_OPEN
        elevator.door_open = True
        self._notify_callbacks('state_changed', elevator)
        
        # Hold doors open
        time.sleep(self.config.DOOR_OPEN_TIME)
        
        self._close_doors(elevator)
    
    def _close_doors(self, elevator: Elevator) -> None:
        """Close elevator doors"""
        elevator.state = ElevatorState.DOORS_CLOSING
        self._notify_callbacks('state_changed', elevator)
        
        # Simulate door closing time
        time.sleep(self.config.DOOR_CLOSE_TIME)
        
        elevator.door_open = False
        elevator.state = ElevatorState.IDLE
        self._notify_callbacks('state_changed', elevator)
    
    def move_elevator_step(self, elevator: Elevator) -> bool:
        """
        Move elevator one floor in its current direction
        
        Args:
            elevator: Elevator to move
            
        Returns:
            True if moved successfully
        """
        with self._lock:
            if elevator.state not in [ElevatorState.MOVING_UP, ElevatorState.MOVING_DOWN]:
                return False
            
            # Move one floor
            if elevator.direction == Direction.UP:
                elevator.current_floor += 1
            else:
                elevator.current_floor -= 1
            
            elevator.total_trips += 1
            
            # Check if reached target floor
            if elevator.current_floor == elevator.target_floor:
                elevator.state = ElevatorState.IDLE
                elevator.direction = Direction.NONE
                self._open_doors(elevator)
                return True
            
            return True
    
    def process_completed_requests(self, elevator: Elevator) -> List[ElevatorRequest]:
        """
        Mark requests as completed for an elevator that has reached its destination
        
        Args:
            elevator: Elevator that reached its destination
            
        Returns:
            List of completed requests
        """
        completed = []
        
        with self._lock:
            for request_id in elevator.requests[:]:
                request = self.requests.get(request_id)
                if request and request.target_floor == elevator.current_floor:
                    request.status = RequestStatus.COMPLETED
                    request.completed_at = datetime.now()
                    elevator.requests.remove(request_id)
                    completed.append(request)
                    self._notify_callbacks('request_completed', request)
        
        return completed
    
    def get_elevator_status(self, elevator_id: str) -> Optional[dict]:
        """Get elevator status"""
        elevator = self.building.get_elevator(elevator_id)
        return elevator.to_dict() if elevator else None
    
    def get_pending_requests(self) -> List[ElevatorRequest]:
        """Get all pending requests"""
        return [
            r for r in self.requests.values() 
            if r.status == RequestStatus.PENDING
        ]
    
    def register_callback(self, event: str, callback: Callable) -> None:
        """Register a callback for events"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _notify_callbacks(self, event: str, *args) -> None:
        """Notify registered callbacks"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def emergency_stop(self, elevator_id: str) -> bool:
        """
        Trigger emergency stop for an elevator
        
        Args:
            elevator_id: Elevator ID
            
        Returns:
            True if emergency stop triggered
        """
        with self._lock:
            elevator = self.building.get_elevator(elevator_id)
            if not elevator:
                return False
            
            elevator.state = ElevatorState.EMERGENCY_STOP
            elevator.is_in_emergency = True
            elevator.door_open = False
            
            # Cancel all pending requests for this elevator
            for request_id in elevator.requests:
                if request_id in self.requests:
                    self.requests[request_id].status = RequestStatus.CANCELLED
            
            self._notify_callbacks('emergency', elevator)
            return True
    
    def reset_elevator(self, elevator_id: str) -> bool:
        """
        Reset elevator after emergency
        
        Args:
            elevator_id: Elevator ID
            
        Returns:
            True if reset successful
        """
        with self._lock:
            elevator = self.building.get_elevator(elevator_id)
            if not elevator:
                return False
            
            elevator.state = ElevatorState.IDLE
            elevator.is_in_emergency = False
            elevator.direction = Direction.NONE
            elevator.requests.clear()
            
            return True


class Scheduler:
    """
    Elevator scheduling using SCAN algorithm
    """
    
    def __init__(self, controller: ElevatorController):
        self.controller = controller
    
    def find_best_elevator(self, request: ElevatorRequest) -> Optional[Elevator]:
        """
        Find the best elevator for a request using SCAN algorithm
        
        The SCAN algorithm works like a电梯:
        - Elevator moves in one direction servicing all requests
        - Reverses direction when reaching the end
        - Considers both direction and distance
        
        Args:
            request: The floor request
            
        Returns:
            Best elevator or None
        """
        building = self.controller.building
        best_elevator = None
        best_score = float('-inf')
        
        for elevator in building.elevators:
            if not elevator.can_accept_request(request.passenger_count):
                continue
            
            score = self._calculate_score(elevator, request)
            
            if score > best_score:
                best_score = score
                best_elevator = elevator
        
        return best_elevator
    
    def _calculate_score(self, elevator: Elevator, request: ElevatorRequest) -> float:
        """
        Calculate priority score for elevator assignment
        
        Higher score = better candidate
        
        Args:
            elevator: Candidate elevator
            request: Floor request
            
        Returns:
            Priority score
        """
        score = 1000
        
        # Priority 1: Emergency requests
        if request.is_emergency:
            score += 500
        
        # Priority 2: Available elevators
        if elevator.is_available():
            score += 300
        
        # Priority 3: Same direction
        if elevator.direction == request.direction:
            score += 200
        
        # Priority 4: Closer elevators get higher priority
        distance = abs(elevator.current_floor - request.floor)
        score -= distance * 10
        
        # Priority 5: Less loaded elevators
        score -= elevator.current_load * 5
        
        # Priority 6: Fewer pending requests
        score -= len(elevator.requests) * 20
        
        return score
    
    def assign_request(self, request_id: str) -> bool:
        """
        Assign a request to the best available elevator
        
        Args:
            request_id: Request ID
            
        Returns:
            True if assigned successfully
        """
        request = self.controller.requests.get(request_id)
        if not request:
            return False
        
        elevator = self.find_best_elevator(request)
        
        if elevator:
            return self.controller.assign_request(request_id, elevator.id)
        
        return False
    
    def process_all_requests(self) -> None:
        """Process all pending requests"""
        pending = self.controller.get_pending_requests()
        
        for request in pending:
            self.assign_request(request.id)
    
    def optimize_queue(self, elevator: Elevator) -> List[int]:
        """
        Optimize the order of floor stops for an elevator using SCAN
        
        Args:
            elevator: Elevator to optimize
            
        Returns:
            Ordered list of floor stops
        """
        requests = [
            self.controller.requests[req_id] 
            for req_id in elevator.requests 
            if req_id in self.controller.requests
        ]
        
        if not requests:
            return []
        
        # Get all unique floors to visit
        floors = set()
        for req in requests:
            floors.add(req.floor)
            floors.add(req.target_floor)
        
        current_floor = elevator.current_floor
        direction = elevator.direction
        
        # If idle, determine initial direction
        if direction == Direction.NONE:
            # Look for the closest request
            closest = min(floors, key=lambda f: abs(f - current_floor))
            if closest > current_floor:
                direction = Direction.UP
            else:
                direction = Direction.DOWN
        
        # Sort floors based on direction (SCAN algorithm)
        floors_list = sorted(floors)
        
        if direction == Direction.UP:
            # Go up first, then down
            above = [f for f in floors_list if f >= current_floor]
            below = [f for f in floors_list if f < current_floor]
            return above + below
        else:
            # Go down first, then up
            above = [f for f in floors_list if f > current_floor]
            below = [f for f in floors_list if f <= current_floor]
            return below + above
