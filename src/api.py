"""
REST API endpoints for the elevator management system
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from typing import Dict, Any, Optional
import uuid
import os

from src.config import get_config
from src.models import BuildingManager, Building, Elevator, ElevatorRequest, Direction, RequestStatus, ElevatorState
from src.controller import ElevatorController, Scheduler
from src.safety import SafetyMonitor, ElevatorLogger, SystemMonitor, SafetyEventType


class ElevatorAPI:
    """
    Flask REST API for elevator management
    """
    
    def __init__(self, config=None):
        self.app = Flask(__name__)
        CORS(self.app)
        
        self.config = config or get_config()
        
        # Initialize components
        self.building_manager = BuildingManager()
        self.controllers: Dict[str, ElevatorController] = {}
        self.schedulers: Dict[str, Scheduler] = {}
        self.safety_monitor = SafetyMonitor()
        self.logger = ElevatorLogger()
        self.system_monitor = SystemMonitor()
        
        # Register routes
        self._register_routes()
        
        # Create default building
        self._create_default_building()
    
    def _create_default_building(self) -> None:
        """Create a default building for testing"""
        building = self.building_manager.create_building(
            name="Main Building",
            floor_count=self.config.DEFAULT_FLOORS,
            elevator_count=self.config.DEFAULT_ELEVATORS,
            address="123 Elevator Street"
        )
        
        # Create controller for the building
        self.controllers[building.id] = ElevatorController(building, self.config)
        self.schedulers[building.id] = Scheduler(self.controllers[building.id])
        
        self.logger.log_info(f"Created default building: {building.name}")
    
    def _register_routes(self) -> None:
        """Register all API routes"""
        
        # Serve frontend
        @self.app.route('/')
        def index():
            return send_from_directory(os.path.join(os.path.dirname(__file__), '..'), 'templates/index.html')
        
        # Health check
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            return jsonify({
                'status': 'healthy',
                'system': self.system_monitor.get_stats()
            })
        
        # Building routes
        @self.app.route('/api/buildings', methods=['GET'])
        def get_buildings():
            buildings = self.building_manager.get_all_buildings()
            return jsonify([b.to_dict() for b in buildings])
        
        @self.app.route('/api/buildings', methods=['POST'])
        def create_building():
            data = request.json
            
            building = self.building_manager.create_building(
                name=data.get('name', 'New Building'),
                floor_count=data.get('floor_count', self.config.DEFAULT_FLOORS),
                elevator_count=data.get('elevator_count', self.config.DEFAULT_ELEVATORS),
                address=data.get('address', '')
            )
            
            # Create controller
            self.controllers[building.id] = ElevatorController(building, self.config)
            self.schedulers[building.id] = Scheduler(self.controllers[building.id])
            
            self.logger.log_info(f"Created building: {building.name}")
            return jsonify(building.to_dict()), 201
        
        @self.app.route('/api/buildings/<building_id>', methods=['GET'])
        def get_building(building_id: str):
            building = self.building_manager.get_building(building_id)
            if not building:
                return jsonify({'error': 'Building not found'}), 404
            return jsonify(building.to_dict())
        
        @self.app.route('/api/buildings/<building_id>', methods=['DELETE'])
        def delete_building(building_id: str):
            if self.building_manager.delete_building(building_id):
                if building_id in self.controllers:
                    del self.controllers[building_id]
                if building_id in self.schedulers:
                    del self.schedulers[building_id]
                return jsonify({'message': 'Building deleted'})
            return jsonify({'error': 'Building not found'}), 404
        
        # Elevator routes
        @self.app.route('/api/buildings/<building_id>/elevators', methods=['GET'])
        def get_elevators(building_id: str):
            building = self.building_manager.get_building(building_id)
            if not building:
                return jsonify({'error': 'Building not found'}), 404
            return jsonify([e.to_dict() for e in building.elevators])
        
        @self.app.route('/api/buildings/<building_id>/elevators/<elevator_id>', methods=['GET'])
        def get_elevator(building_id: str, elevator_id: str):
            building = self.building_manager.get_building(building_id)
            if not building:
                return jsonify({'error': 'Building not found'}), 404
            
            elevator = building.get_elevator(elevator_id)
            if not elevator:
                return jsonify({'error': 'Elevator not found'}), 404
            
            return jsonify(elevator.to_dict())
        
        @self.app.route('/api/buildings/<building_id>/elevators/<elevator_id>/move', methods=['POST'])
        def move_elevator(building_id: str, elevator_id: str):
            building = self.building_manager.get_building(building_id)
            if not building:
                return jsonify({'error': 'Building not found'}), 404
            
            elevator = building.get_elevator(elevator_id)
            if not elevator:
                return jsonify({'error': 'Elevator not found'}), 404
            
            data = request.json
            target_floor = data.get('target_floor')
            
            if target_floor is None:
                return jsonify({'error': 'target_floor is required'}), 400
            
            if target_floor < 0 or target_floor >= len(building.floors):
                return jsonify({'error': 'Invalid floor number'}), 400
            
            controller = self.controllers.get(building_id)
            if not controller:
                return jsonify({'error': 'Controller not found'}), 500
            
            # Set target and start elevator
            elevator.target_floor = target_floor
            controller.start_elevator(elevator_id)
            
            self.logger.log_elevator_state(elevator, building)
            
            return jsonify(elevator.to_dict())
        
        @self.app.route('/api/buildings/<building_id>/elevators/<elevator_id>/emergency-stop', methods=['POST'])
        def emergency_stop(building_id: str, elevator_id: str):
            building = self.building_manager.get_building(building_id)
            if not building:
                return jsonify({'error': 'Building not found'}), 404
            
            elevator = building.get_elevator(elevator_id)
            if not elevator:
                return jsonify({'error': 'Elevator not found'}), 404
            
            controller = self.controllers.get(building_id)
            if not controller:
                return jsonify({'error': 'Controller not found'}), 500
            
            reason = request.json.get('reason', 'Manual emergency stop') if request.json else 'Manual emergency stop'
            
            controller.emergency_stop(elevator_id)
            self.safety_monitor.trigger_emergency(elevator, building, reason)
            self.logger.log_emergency(elevator, building, reason)
            
            return jsonify({
                'message': 'Emergency stop activated',
                'elevator': elevator.to_dict()
            })
        
        @self.app.route('/api/buildings/<building_id>/elevators/<elevator_id>/reset', methods=['POST'])
        def reset_elevator(building_id: str, elevator_id: str):
            building = self.building_manager.get_building(building_id)
            if not building:
                return jsonify({'error': 'Building not found'}), 404
            
            elevator = building.get_elevator(elevator_id)
            if not elevator:
                return jsonify({'error': 'Elevator not found'}), 404
            
            controller = self.controllers.get(building_id)
            if not controller:
                return jsonify({'error': 'Controller not found'}), 500
            
            controller.reset_elevator(elevator_id)
            
            self.logger.log_info(f"Elevator {elevator.name} reset", building)
            
            return jsonify({
                'message': 'Elevator reset successfully',
                'elevator': elevator.to_dict()
            })
        
        # Request routes
        @self.app.route('/api/buildings/<building_id>/requests', methods=['POST'])
        def create_request(building_id: str):
            building = self.building_manager.get_building(building_id)
            if not building:
                return jsonify({'error': 'Building not found'}), 404
            
            data = request.json
            
            floor = data.get('floor')
            target_floor = data.get('target_floor')
            passenger_count = data.get('passenger_count', 1)
            is_emergency = data.get('is_emergency', False)
            
            if floor is None or target_floor is None:
                return jsonify({'error': 'floor and target_floor are required'}), 400
            
            if floor < 0 or floor >= len(building.floors):
                return jsonify({'error': 'Invalid floor'}), 400
            if target_floor < 0 or target_floor >= len(building.floors):
                return jsonify({'error': 'Invalid target floor'}), 400
            
            controller = self.controllers.get(building_id)
            if not controller:
                return jsonify({'error': 'Controller not found'}), 500
            
            # Check for overload
            if self.safety_monitor.check_overload(Elevator(capacity=8), passenger_count):
                return jsonify({'error': 'Overload - too many passengers'}), 400
            
            # Create request
            request_obj = controller.add_request(
                floor=floor,
                target_floor=target_floor,
                passenger_count=passenger_count,
                is_emergency=is_emergency
            )
            
            # Auto-assign using scheduler
            scheduler = self.schedulers.get(building_id)
            if scheduler:
                scheduler.assign_request(request_obj.id)
                
                # If assigned, start the elevator
                if request_obj.assigned_elevator_id:
                    controller.start_elevator(request_obj.assigned_elevator_id)
            
            self.logger.log_request(request_obj, building, "created")
            self.system_monitor.record_request(True)
            
            return jsonify(request_obj.to_dict()), 201
        
        @self.app.route('/api/buildings/<building_id>/requests', methods=['GET'])
        def get_requests(building_id: str):
            building = self.building_manager.get_building(building_id)
            if not building:
                return jsonify({'error': 'Building not found'}), 404
            
            controller = self.controllers.get(building_id)
            if not controller:
                return jsonify({'error': 'Controller not found'}), 500
            
            status = request.args.get('status')
            requests = list(controller.requests.values())
            
            if status:
                requests = [r for r in requests if r.status.value == status]
            
            return jsonify([r.to_dict() for r in requests])
        
        @self.app.route('/api/buildings/<building_id>/requests/<request_id>', methods=['GET'])
        def get_request(building_id: str, request_id: str):
            building = self.building_manager.get_building(building_id)
            if not building:
                return jsonify({'error': 'Building not found'}), 404
            
            controller = self.controllers.get(building_id)
            if not controller:
                return jsonify({'error': 'Controller not found'}), 500
            
            request_obj = controller.requests.get(request_id)
            if not request_obj:
                return jsonify({'error': 'Request not found'}), 404
            
            return jsonify(request_obj.to_dict())
        
        # Safety routes
        @self.app.route('/api/safety/events', methods=['GET'])
        def get_safety_events():
            elevator_id = request.args.get('elevator_id')
            building_id = request.args.get('building_id')
            limit = int(request.args.get('limit', 100))
            
            events = self.safety_monitor.get_events(
                elevator_id=elevator_id,
                building_id=building_id,
                limit=limit
            )
            
            return jsonify([e.to_dict() for e in events])
        
        @self.app.route('/api/safety/check/<building_id>/<elevator_id>', methods=['GET'])
        def safety_check(building_id: str, elevator_id: str):
            building = self.building_manager.get_building(building_id)
            if not building:
                return jsonify({'error': 'Building not found'}), 404
            
            elevator = building.get_elevator(elevator_id)
            if not elevator:
                return jsonify({'error': 'Elevator not found'}), 404
            
            safety_status = self.safety_monitor.check_elevator_safe(elevator)
            
            return jsonify(safety_status)
        
        # Statistics
        @self.app.route('/api/stats', methods=['GET'])
        def get_stats():
            return jsonify(self.system_monitor.get_stats())
    
    def run(self, host: str = None, port: int = None, debug: bool = None) -> None:
        """Run the Flask application"""
        host = host or self.config.HOST
        port = port or self.config.PORT
        debug = debug if debug is not None else self.config.DEBUG
        
        self.app.run(host=host, port=port, debug=debug)


def create_app(config=None) -> Flask:
    """
    Create Flask application
    
    Args:
        config: Configuration object
        
    Returns:
        Flask application
    """
    api = ElevatorAPI(config)
    return api.app
