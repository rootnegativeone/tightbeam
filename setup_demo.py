#!/usr/bin/env python3
"""
Tightbeam Demo Setup Script
Automates the setup and running of the encoder demo.
"""
import subprocess
import sys
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Error: Python 3.7 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        print("   Please upgrade Python and try again")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True

def install_dependencies():
    """Install required Python packages."""
    print("📦 Installing dependencies...")
    
    try:
        # Check if requirements.txt exists
        if not Path("requirements.txt").exists():
            print("❌ Error: requirements.txt not found")
            print("   Make sure you're running this from the tightbeam directory")
            return False
        
        # Install packages
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print("❌ Error installing dependencies:")
            print(result.stderr)
            print("\n💡 Try running manually:")
            print("   pip install -r requirements.txt")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def run_demo():
    """Run the standalone encoder demo."""
    print("🚀 Running Tightbeam encoder demo...")
    print("-" * 50)
    
    try:
        # Change to demo directory and run
        demo_path = Path("demo/standalone_encoder.py")
        if not demo_path.exists():
            print("❌ Error: Demo script not found")
            print("   Expected: demo/standalone_encoder.py")
            return False
        
        # Run the demo
        result = subprocess.run([sys.executable, str(demo_path)], 
                              cwd=Path.cwd())
        
        if result.returncode == 0:
            print("\n" + "=" * 50)
            print("✅ Demo completed successfully!")
            return True
        else:
            print("❌ Demo failed with error code:", result.returncode)
            return False
            
    except Exception as e:
        print(f"❌ Error running demo: {e}")
        return False

def main():
    """Main setup and demo runner."""
    print("=" * 60)
    print("🎯 TIGHTBEAM DEMO SETUP")
    print("=" * 60)
    print()
    
    # Step 1: Check Python version
    print("1️⃣  Checking Python version...")
    if not check_python_version():
        sys.exit(1)
    print()
    
    # Step 2: Install dependencies
    print("2️⃣  Installing dependencies...")
    if not install_dependencies():
        print("\n💡 Manual installation:")
        print("   pip install opencv-python qrcode Pillow numpy imageio")
        response = input("\nContinue anyway? (y/N): ").lower().strip()
        if response != 'y':
            sys.exit(1)
    print()
    
    # Step 3: Run demo
    print("3️⃣  Running demo...")
    if not run_demo():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 SETUP AND DEMO COMPLETE!")
    print("=" * 60)
    print()
    print("📁 Output files created:")
    print("   • tightbeam_demo.gif - QR-GIF for display")
    print("   • sample_log.json - Sample of encoded data")
    print()
    print("📱 Next steps:")
    print("   1. Open tightbeam_demo.gif on any device")
    print("   2. Scan the QR codes with a camera/phone")
    print("   3. Each QR contains: 'index:hex_payload'")
    print()

if __name__ == "__main__":
    main()
