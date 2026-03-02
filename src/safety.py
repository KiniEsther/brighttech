"""
Safety systems and logging for the elevator management
"""
import logging
import threading
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum
from src.models import Elevator, ElevatorRequest, Building, ElevatorState


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    EMERGENCY = "EMERGENCY"


class SafetyEventType(Enum):
    """Types of safety events"""
    EMERGENCY_STOP = "emergency_stop"
    OVERLOAD = "overload"
    DOOR_SENSOR = "door_sensor"
    MAINTENANCE_DUE = "maintenance_due"
    SYSTEM_ERROR = "system_error"
    FIRE_ALARM = "fire_alarm"
    POWER_FAILURE = "power_failure"


class SafetyEvent:
    """Represents a safety event"""
    def __init__(
        self,
        event_type: SafetyEventType,
        elevator_id: str,
        building_id: str,
        severity: str = "INFO",
        description: str = "",
        data: dict = None
    ):
        self.id = f"SE-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        self.event_type = event_type
        self.elevator_id = elevator_id
        self.building_id = building_id
        self.severity = severity
        self.description = description
        self.data = data or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'event_type': self.event_type.value,
            'elevator_id': self.elevator_id,
            'building_id': self.building_id,
            'severity': self.severity,
            'description': self.description,
            'data': self.data,
            'timestamp': self.timestamp.isoformat()
        }


class SafetyMonitor:
    """
    Monitors elevator safety systems
    """
    
    def __init__(self):
        self._events: List[SafetyEvent] = []
        self._lock = threading.RLock()
        self._emergency_active = False
        self._callbacks: List[callable] = []
    
    def log_event(
        self,
        event_type: SafetyEventType,
        elevator: Elevator,
        building: Building,
        severity: str = "INFO",
        description: str = "",
        data: dict = None
    ) -> SafetyEvent:
        """
        Log a safety event
        
        Args:
            event_type: Type of safety event
            elevator: Related elevator
            building: Building
            severity: Event severity
            description: Description
            additional data
            
        Returns:
            Created safety event
        """
        with self._lock:
            event = SafetyEvent(
                event_type=event_type,
                elevator_id=elevator.id,
                building_id=building.id,
                severity=severity,
                description=description,
                data=data
            )
            self._events.append(event)
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Safety event callback error: {e}")
            
            return event
    
    def check_overload(
        self, 
        elevator: Elevator, 
        passenger_count: int
    ) -> bool:
        """
        Check if adding passengers would cause overload
        
        Args:
            elevator: Elevator to check
            passenger_count: Passengers to add
            
        Returns:
            True if overload would occur
        """
        new_load = elevator.current_load + passenger_count
        return new_load > elevator.capacity
    
    def check_elevator_safe(self, elevator: Elevator) -> Dict[str, Any]:
        """
        Check if elevator is in a safe state
        
        Args:
            elevator: Elevator to check
            
        Returns:
            Dictionary with safety status
        """
        issues = []
        
        if elevator.is_in_emergency:
            issues.append("Elevator in emergency stop")
        
        if not elevator.is_operational:
            issues.append("Elevator not operational")
        
        if elevator.current_load > elevator.capacity:
            issues.append("Overload detected")
        
        if elevator.door_open and elevator.state not in [
            ElevatorState.DOORS_OPENING,
            ElevatorState.DOORS_OPEN,
            ElevatorState.DOORS_CLOSING
        ]:
            issues.append("Door state inconsistency")
        
        return {
            'safe': len(issues) == 0,
            'issues': issues
        }
    
    def trigger_emergency(
        self,
        elevator: Elevator,
        building: Building,
        reason: str = ""
    ) -> SafetyEvent:
        """
        Trigger emergency stop for an elevator
        
        Args:
            elevator: Elevator
            building: Building
            reason: Emergency reason
            
        Returns:
            Safety event
        """
        self._emergency_active = True
        
        return self.log_event(
            event_type=SafetyEventType.EMERGENCY_STOP,
            elevator=elevator,
            building=building,
            severity="CRITICAL",
            description=f"Emergency stop triggered: {reason}",
            data={'reason': reason}
        )
    
    def register_callback(self, callback: callable) -> None:
        """Register callback for safety events"""
        self._callbacks.append(callback)
    
    def get_events(
        self, 
        elevator_id: str = None,
        building_id: str = None,
        limit: int = 100
    ) -> List[SafetyEvent]:
        """
        Get safety events with optional filters
        
        Args:
            elevator_id: Filter by elevator
            building_id: Filter by building
            limit: Maximum events to return
            
        Returns:
            List of safety events
        """
        with self._lock:
            events = self._events
            
            if elevator_id:
                events = [e for e in events if e.elevator_id == elevator_id]
            
            if building_id:
                events = [e for e in events if e.building_id == building_id]
            
            return events[-limit:]


class ElevatorLogger:
    """
    Comprehensive logging for elevator operations
    """
    
    def __init__(self, name: str = "ElevatorSystem"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler('elevator.log')
        file_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def log_elevator_state(
        self, 
        elevator: Elevator, 
        building: Building
    ) -> None:
        """Log elevator state change"""
        self.logger.info(
            f"Building: {building.name} | "
            f"Elevator: {elevator.name} | "
            f"Floor: {elevator.current_floor} | "
            f"State: {elevator.state.value} | "
            f"Direction: {elevator.direction.value}"
        )
    
    def log_request(
        self, 
        request: ElevatorRequest, 
        building: Building,
        action: str = "created"
    ) -> None:
        """Log request action"""
        self.logger.info(
            f"Building: {building.name} | "
            f"Request: {request.id[:8]} | "
            f"Action: {action} | "
            f"Floor: {request.floor} -> {request.target_floor} | "
            f"Status: {request.status.value}"
        )
    
    def log_assignment(
        self,
        request: ElevatorRequest,
        elevator: Elevator,
        building: Building
    ) -> None:
        """Log request assignment"""
        self.logger.info(
            f"Building: {building.name} | "
            f"Request: {request.id[:8]} | "
            f"Assigned to: {elevator.name} | "
            f"Current floor: {elevator.current_floor}"
        )
    
    def log_emergency(
        self,
        elevator: Elevator,
        building: Building,
        reason: str
    ) -> None:
        """Log emergency event"""
        self.logger.critical(
            f"Building: {building.name} | "
            f"Elevator: {elevator.name} | "
            f"EMERGENCY: {reason}"
        )
    
    def log_error(
        self,
        message: str,
        building: Building = None,
        elevator: Elevator = None
    ) -> None:
        """Log error"""
        context = ""
        if building:
            context += f"Building: {building.name} | "
        if elevator:
            context += f"Elevator: {elevator.name} | "
        
        self.logger.error(f"{context}{message}")
    
    def log_warning(self, message: str, building: Building = None) -> None:
        """Log warning"""
        context = f"Building: {building.name} | " if building else ""
        self.logger.warning(f"{context}{message}")
    
    def log_info(self, message: str, building: Building = None) -> None:
        """Log info"""
        context = f"Building: {building.name} | " if building else ""
        self.logger.info(f"{context}{message}")


class SystemMonitor:
    """
    Monitors overall system health
    """
    
    def __init__(self):
        self._start_time = datetime.now()
        self._total_requests = 0
        self._completed_requests = 0
        self._failed_requests = 0
    
    def record_request(self, success: bool = True) -> None:
        """Record a request"""
        self._total_requests += 1
        if success:
            self._completed_requests += 1
        else:
            self._failed_requests += 1
    
    def get_stats(self) -> dict:
        """Get system statistics"""
        uptime = (datetime.now() - self._start_time).total_seconds()
        
        return {
            'uptime_seconds': uptime,
            'total_requests': self._total_requests,
            'completed_requests': self._completed_requests,
            'failed_requests': self._failed_requests,
            'success_rate': (
                self._completed_requests / self._total_requests * 100
                if self._total_requests > 0 else 0
            )
        }
