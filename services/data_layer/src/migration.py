#!/usr/bin/env python3
"""
Database migration utility script.

This script provides a simplified interface to run Alembic migrations.
"""

import argparse
import logging
import os
import sys
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_alembic_path():
    """Get the path to the Alembic configuration file."""
    current_file = Path(__file__)
    parent_dir = current_file.parent.parent
    return parent_dir / "alembic.ini"


def run_alembic_command(command, *args):
    """Run an Alembic command."""
    alembic_ini = get_alembic_path()
    
    # Ensure the alembic.ini file exists
    if not alembic_ini.exists():
        logger.error(f"Alembic config file not found at {alembic_ini}")
        return 1
    
    # Build the command
    cmd = ["alembic", "-c", str(alembic_ini), command]
    
    # Add any additional arguments
    if args:
        cmd.extend(args)
    
    logger.info(f"Running Alembic command: {' '.join(cmd)}")
    
    # Run the command
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        logger.error(f"Alembic command failed: {e}")
        return e.returncode


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(description='Run database migrations')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Migration command')
    
    # Initialize migrations
    init_parser = subparsers.add_parser('init', help='Initialize migrations')
    
    # Create a new migration
    revision_parser = subparsers.add_parser('revision', help='Create a new migration')
    revision_parser.add_argument('--message', '-m', help='Migration message')
    revision_parser.add_argument('--autogenerate', '-a', action='store_true', 
                               help='Autogenerate migration from models')
    
    # Upgrade database
    upgrade_parser = subparsers.add_parser('upgrade', help='Upgrade database')
    upgrade_parser.add_argument('--revision', help='Revision to upgrade to (default: head)')
    
    # Downgrade database
    downgrade_parser = subparsers.add_parser('downgrade', help='Downgrade database')
    downgrade_parser.add_argument('--revision', help='Revision to downgrade to')
    
    # Show current version
    subparsers.add_parser('current', help='Show current database version')
    
    # Show migration history
    subparsers.add_parser('history', help='Show migration history')
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no command is provided, show help
    if not args.command:
        parser.print_help()
        return 1
    
    # Run the appropriate command
    if args.command == 'init':
        return run_alembic_command('init', 'migrations')
    
    elif args.command == 'revision':
        cmd_args = []
        if args.message:
            cmd_args.extend(['-m', args.message])
        if args.autogenerate:
            cmd_args.append('--autogenerate')
        return run_alembic_command('revision', *cmd_args)
    
    elif args.command == 'upgrade':
        revision = args.revision or 'head'
        return run_alembic_command('upgrade', revision)
    
    elif args.command == 'downgrade':
        if not args.revision:
            logger.error("Revision is required for downgrade")
            return 1
        return run_alembic_command('downgrade', args.revision)
    
    elif args.command == 'current':
        return run_alembic_command('current')
    
    elif args.command == 'history':
        return run_alembic_command('history')
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 