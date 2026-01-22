import launch

# Check for 'requests' library (used for API calls)
if not launch.is_installed("requests"):
    print("Wavespeed Upscaler: Installing 'requests'...")
    launch.run_pip("install requests", "requests")

# Check for 'Pillow' (PIL) - usually standard, but good to ensure
if not launch.is_installed("Pillow"):
    print("Wavespeed Upscaler: Installing 'Pillow'...")
    launch.run_pip("install Pillow", "Pillow")