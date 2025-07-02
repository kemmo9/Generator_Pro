import subprocess
import sys

def run_command(command):
    """Runs a command and raises an exception if it fails."""
    print(f"--- Running command: {' '.join(command)} ---")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Stream the output in real-time
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
            
    # Check for errors
    if process.returncode != 0:
        print(f"--- Command failed with exit code {process.returncode} ---")
        sys.exit(process.returncode)
    else:
        print("--- Command successful ---")

def main():
    print("--- Starting build process ---")
    
    # Step 1: Update package lists for system dependencies
    run_command(["apt-get", "update", "-y"])
    
    # Step 2: Install ImageMagick
    # We also install its delegates to handle various image formats robustly.
    run_command([
        "apt-get", "install", "-y", 
        "imagemagick",
        "libmagickwand-dev"
    ])
    
    # Step 3: Install Python dependencies from requirements.txt
    run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    print("\n--- Build process completed successfully! ---")

if __name__ == "__main__":
    main()
