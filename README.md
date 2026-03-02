# Elevator Management System

A professional backend system for controlling and managing multiple elevators in a building.

## Features

- Multi-elevator management
- Real-time elevator scheduling using SCAN algorithm
- Floor request management
- Elevator state tracking
- REST API for external integration
- Safety systems (overload, emergency stop)
- Comprehensive logging

## API Endpoints

### Building Management

- `GET /api/buildings` - List all buildings
- `POST /api/buildings` - Create a new building
- `GET /api/buildings/{id}` - Get building details

### Elevator Management

- `GET /api/buildings/{building_id}/elevators` - List all elevators in a building
- `GET /api/buildings/{building_id}/elevators/{elevator_id}` - Get elevator details
- `POST /api/buildings/{building_id}/elevators/{elevator_id}/emergency-stop` - Trigger emergency stop
- `POST /api/buildings/{building_id}/elevators/{elevator_id}/reset` - Reset elevator after emergency

### Request Management

- `POST /api/buildings/{building_id}/requests` - Create a floor request
- `GET /api/buildings/{building_id}/requests` - Get all pending requests

## Running the Application

```bash
pip install -r requirements.txt
python3 src/main.py
```

The server will start on http://localhost:5000

## Architecture

- **Controller Service**: Manages elevator operations and scheduling
- **Scheduler**: Implements SCAN algorithm for efficient elevator scheduling
- **Safety Monitor**: Handles emergency situations and safety checks
- **API Layer**: RESTful endpoints for external communication
