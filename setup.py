#!/usr/bin/env python3
import subprocess
import sys
import os

def install_requirements():
    """Install required packages"""
    print("Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Packages installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install packages: {e}")
        return False
    return True

def install_playwright():
    """Install Playwright browsers"""
    print("Installing Playwright browsers...")
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        print("✓ Playwright browsers installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install Playwright browsers: {e}")
        return False
    return True

def main():
    print("Setting up Picture Downloader...")
    
    if not install_requirements():
        sys.exit(1)
    
    if not install_playwright():
        sys.exit(1)
    
    print("\n✓ Setup complete!")
    print("\nUsage:")
    print('python pic_downloader.py "michael jordan"')

if __name__ == "__main__":
    main()