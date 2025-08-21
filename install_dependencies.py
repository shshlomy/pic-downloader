#!/usr/bin/env python3
"""
Install dependencies for content-aware filtering
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a Python package"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def main():
    print("🚀 Installing Content-Aware Filtering Dependencies")
    print("="*60)
    
    packages = [
        "opencv-python==4.8.1.78",
        "numpy==1.24.3", 
        "mediapipe==0.10.8",
        # Skip ML packages for now as they're large
        # "transformers==4.35.2",
        # "torch==2.1.1", 
        # "torchvision==0.16.1"
    ]
    
    success_count = 0
    for package in packages:
        print(f"📦 Installing {package}...")
        if install_package(package):
            print(f"   ✅ {package} installed successfully")
            success_count += 1
        else:
            print(f"   ❌ Failed to install {package}")
    
    print(f"\n{'='*60}")
    print(f"📊 Installation Summary: {success_count}/{len(packages)} packages installed")
    
    if success_count == len(packages):
        print("✅ All dependencies installed successfully!")
        print("\n🎯 You can now test the content-aware filtering:")
        print('   python3 test_content_filter.py "downloads/agam buhbut" "agam buhbut"')
    else:
        print("⚠️  Some dependencies failed to install. The system may not work properly.")
    
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
