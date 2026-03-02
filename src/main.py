"""
Main entry point for the Elevator Management System
"""
import os
import sys
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_config
from src.api import ElevatorAPI


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Elevator Management System'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default=None,
        help='Host to bind the server to'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='Port to bind the server to'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    parser.add_argument(
        '--env',
        type=str,
        choices=['development', 'production', 'testing'],
        default='development',
        help='Environment to run in'
    )
    
    parser.add_argument(
        '--floors',
        type=int,
        default=10,
        help='Number of floors in the default building'
    )
    
    parser.add_argument(
        '--elevators',
        type=int,
        default=2,
        help='Number of elevators in the default building'
    )
    
    return parser.parse_args()


def print_banner():
    """Print application banner"""
    banner = """
    ╔═══════════════════════════════════════════════════╗
    ║         ELEVATOR MANAGEMENT SYSTEM                ║
    ║              Professional Edition                 ║
    ╠═══════════════════════════════════════════════════╣
    ║  Building Elevator Control & Management Backend   ║
    ╚═══════════════════════════════════════════════════╝
    """
    print(banner)


def print_info(config):
    """Print configuration info"""
    print(f"\n[INFO] Starting Elevator Management System")
    print(f"[INFO] Environment: {config.__class__.__name__}")
    print(f"[INFO] Debug: {config.DEBUG}")
    print(f"[INFO] Host: {config.HOST}")
    print(f"[INFO] Port: {config.PORT}")
    print(f"[INFO] Default Floors: {config.DEFAULT_FLOORS}")
    print(f"[INFO] Default Elevators: {config.DEFAULT_ELEVATORS}")
    print()


def main():
    """Main entry point"""
    # Parse arguments
    args = parse_args()
    
    # Get configuration
    config = get_config(args.env)
    
    # Override config with command line args
    if args.host:
        config.HOST = args.host
    if args.port:
        config.PORT = args.port
    if args.debug:
        config.DEBUG = True
    
    # Override default floors/elevators if specified
    if args.floors:
        config.DEFAULT_FLOORS = args.floors
    if args.elevators:
        config.DEFAULT_ELEVATORS = args.elevators
    
    # Print banner
    print_banner()
    
    # Print info
    print_info(config)
    
    # Create and run API
    try:
        api = ElevatorAPI(config)
        print("[INFO] API initialized successfully")
        print(f"[INFO] Server starting on http://{config.HOST}:{config.PORT}")
        print("[INFO] Press CTRL+C to stop the server\n")
        
        api.run(
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG
        )
        
    except KeyboardInterrupt:
        print("\n\n[INFO] Shutting down Elevator Management System...")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n[ERROR] Failed to start server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
