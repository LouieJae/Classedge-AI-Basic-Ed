#!/usr/bin/env python3
"""
Setup script for ClassEdge LMS virtual environment.
Creates a virtual environment and installs dependencies.
"""

import os
import sys
import subprocess
import platform


def main():
    print("Setting up virtual environment for ClassEdge LMS...")
    print()
    
    # Create a virtual environment
    print("Creating virtual environment...")
    try:
        subprocess.run([sys.executable, "-m", "venv", "env"], check=True)
        print("✓ Virtual environment created successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create virtual environment: {e}")
        return 1
    
    # Determine the activation script path based on OS
    if platform.system() == "Windows":
        pip_path = os.path.join("env", "Scripts", "pip")
        activate_cmd = "env\\Scripts\\activate.bat"
    else:
        pip_path = os.path.join("env", "bin", "pip")
        activate_cmd = "source env/bin/activate"
    
    # Install requirements
    print()
    print("Installing dependencies from requirements.txt...")
    try:
        subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return 1
    
    # Success message
    print()
    print("=" * 60)
    print("Environment setup complete!")
    print("=" * 60)
    print()
    print("To activate the environment in the future, run:")
    print(f"    {activate_cmd}")
    print()
    print("To deactivate the environment when done, run:")
    print("    deactivate")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
