apt-get update -y
apt-get install -y ffmpeg
python3 processing/sync_kb.py
# Start the Python application
python -m gunicorn --bind=0.0.0.0 --timeout 600 app:app