import subprocess
import sys
import os

def install_package(package):
    print(f"Installing {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

print("Setting up audio dependencies for Smokey's Radio...")

# Essential packages
packages = [
    "PyNaCl",        # Required for voice
    "discord.py[voice]",
    "yt-dlp",
    "python-dotenv"
]

# Install each package
for package in packages:
    install_package(package)

# Check for FFmpeg
try:
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ FFmpeg is installed and working")
    else:
        print("❌ FFmpeg is not working properly")
except FileNotFoundError:
    print("❌ FFmpeg not found. Installing ffmpeg directory...")
    
    # Create bin directory if it doesn't exist
    os.makedirs("bin/ffmpeg", exist_ok=True)
    
    # Download FFmpeg (for Windows)
    import urllib.request
    import zipfile
    
    print("Downloading FFmpeg... (this may take a few minutes)")
    url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    zip_path = "bin/ffmpeg.zip"
    
    urllib.request.urlretrieve(url, zip_path)
    
    print("Extracting FFmpeg...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall("bin")
    
    # Rename and cleanup
    import shutil
    extracted_dir = "bin/ffmpeg-master-latest-win64-gpl"
    
    # Copy the ffmpeg.exe file to the bin/ffmpeg directory
    if os.path.exists(f"{extracted_dir}/bin/ffmpeg.exe"):
        shutil.copy(f"{extracted_dir}/bin/ffmpeg.exe", "bin/ffmpeg/ffmpeg.exe")
        print("✅ FFmpeg installed successfully")
    
    # Clean up
    if os.path.exists(zip_path):
        os.remove(zip_path)

print("\nSetup complete! You should now be able to use voice features.") 