# File Compression Watcher

This script acts as a system janitor. It runs in the background (as a daemon), looks for large files in a specific folder, compresses them to save space, and sends you an email report of its progress.

## INSTALL NOTES:  
   You'll need Python 3.x or higher.
   You'll need to ensure these additional modules are installed:  
   pip install validate-email-address
   pip install psutil
