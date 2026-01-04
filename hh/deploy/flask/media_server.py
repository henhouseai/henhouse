#!/usr/bin/env python3
"""
Media Server Flask App for Henhouse
Dedicated Flask app for serving media files (downloads and streams).
Runs as admin user to access /srv/{media_type}/{project_name} directories.
Only exposes download/stream routes - no MCP, no show pages, no arbitrary gateway access.
"""

import sys
import os
import logging
import subprocess
import threading
from pathlib import Path
from flask import Flask, request, send_file

# Determine project name from /srv path or environment
if os.path.exists('/srv'):
    cwd = Path.cwd()
    if str(cwd).startswith('/srv/'):
        PROJECT_NAME = cwd.name
    else:
        PROJECT_NAME = os.getenv('PROJECT_NAME', 'henhouse')
else:
    PROJECT_NAME = os.getenv('PROJECT_NAME', 'henhouse')

# Setup paths
PROJECT_ROOT = Path(f'/srv/{PROJECT_NAME}')

# Get log file (set by deploy script)
LOG_FILE = os.getenv('LOG_FILE', f'/srv/{PROJECT_NAME}/logs/flask_{PROJECT_NAME}_media.log')

# Create Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', f'{PROJECT_NAME}-media-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit

# Configure Flask's logger to write to our log file
# Note: Log file should already exist (created by flask_start script)
if LOG_FILE and Path(LOG_FILE).exists():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s [Media Server] %(levelname)s %(message)s'
    )

# Log initialization after logging is configured
logging.info(f"Media Server Flask app initialized: PROJECT_NAME={PROJECT_NAME}")

GATEWAY_MAX_CONCURRENCY = int(os.getenv('GATEWAY_MAX_CONCURRENCY', '4'))
_gateway_semaphore = threading.Semaphore(GATEWAY_MAX_CONCURRENCY)


@app.route("/file/<int:file_id>/download", methods=["GET"])
def download_file(file_id: int):
    """Download a file by ID using the download backend for metadata, then serve from disk."""
    import json

    cmd = ['python3', str(PROJECT_ROOT / 'download_client.py'), 'get_file_info', '--id', str(file_id)]

    acquired = _gateway_semaphore.acquire(timeout=10)
    if not acquired:
        logging.error("Gateway concurrency limit reached for download request")
        return "Server busy, please retry", 503

    try:
        env = os.environ.copy()
        # Media server runs as admin user, but we still need to set USER_TIER for download_client
        # Use 'admin' tier for media server (it has access to all media)
        env['USER_TIER'] = 'admin'
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(PROJECT_ROOT),
            env=env,
        )
    finally:
        _gateway_semaphore.release()

    if result.returncode != 0 or not result.stdout:
        logging.warning(
            "download_client failed for file_id=%s, rc=%s, stdout=%s, stderr=%s",
            file_id,
            result.returncode,
            (result.stdout or "").strip(),
            (result.stderr or "").strip(),
        )
        return "File not found", 404

    try:
        resp = json.loads(result.stdout)
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON from download_client for file_id={file_id}: {result.stdout[:200]}")
        return "Internal error", 500

    if resp.get("status") != "ok":
        logging.info(f"Download metadata error for file_id={file_id}: {resp.get('errors')}")
        return "File not found", 404

    file_info = (resp.get("data") or {}).get("file") or {}
    rel_path = file_info.get("file_path")
    if not rel_path:
        logging.info(f"No file_path in metadata for file_id={file_id}")
        return "File not found", 404

    base_path = Path(f"/srv/files/{PROJECT_NAME}")
    abs_path = base_path / rel_path

    try:
        if not abs_path.exists():
            logging.info(f"File path missing on disk for file_id={file_id}: {abs_path}")
            return "File not found", 404
    except PermissionError:
        logging.warning(f"Permission denied checking file existence for file_id={file_id}: {abs_path}")
        return "Permission denied", 403

    download_name = file_info.get("file_name") or abs_path.name
    mime_type = file_info.get("mime_type") or "application/octet-stream"

    logging.info(f"Media Server: Serving file download file_id={file_id}, name={download_name}")
    return send_file(
        abs_path,
        mimetype=mime_type,
        as_attachment=True,
        download_name=download_name,
        conditional=True,
    )


@app.route('/img/<int:image_id>/download', methods=['GET'])
def download_image(image_id: int):
    """Download an image by ID using the download backend for metadata, then serve from disk."""
    import json

    cmd = ['python3', str(PROJECT_ROOT / 'download_client.py'), 'get_image_info', '--id', str(image_id)]

    acquired = _gateway_semaphore.acquire(timeout=10)
    if not acquired:
        logging.error("Gateway concurrency limit reached for image download request")
        return "Server busy, please retry", 503

    try:
        env = os.environ.copy()
        env['USER_TIER'] = 'admin'
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(PROJECT_ROOT),
            env=env,
        )
    finally:
        _gateway_semaphore.release()

    if result.returncode != 0 or not result.stdout:
        logging.warning(
            "download_client failed for image_id=%s, rc=%s, stdout=%s, stderr=%s",
            image_id,
            result.returncode,
            (result.stdout or "").strip(),
            (result.stderr or "").strip(),
        )
        return "Image not found", 404

    try:
        resp = json.loads(result.stdout)
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON from download_client for image_id={image_id}: {result.stdout[:200]}")
        return "Internal error", 500

    if resp.get("status") != "ok":
        logging.info(f"Download metadata error for image_id={image_id}: {resp.get('errors')}")
        return "Image not found", 404

    image_info = (resp.get("data") or {}).get("image") or {}
    instances = image_info.get("instances", [])
    if not instances:
        logging.info(f"No instances in metadata for image_id={image_id}")
        return "Image not found", 404
    
    # Get full-size instance (usually the first one or largest)
    full_instance = None
    for instance in instances:
        if instance.get("instance_type") == "full" or instance.get("width", 0) > 0:
            full_instance = instance
            break
    
    if not full_instance:
        full_instance = instances[0]
    
    rel_path = full_instance.get("src")
    if not rel_path:
        logging.info(f"No src in instance metadata for image_id={image_id}")
        return "Image not found", 404

    base_path = Path(f"/srv/images/{PROJECT_NAME}")
    abs_path = base_path / rel_path

    try:
        if not abs_path.exists():
            logging.info(f"Image path missing on disk for image_id={image_id}: {abs_path}")
            return "Image not found", 404
    except PermissionError:
        logging.warning(f"Permission denied checking image existence for image_id={image_id}: {abs_path}")
        return "Permission denied", 403

    download_name = image_info.get("caption") or f"image_{image_id}.jpg"
    mime_type = "image/jpeg"  # Default, could be determined from file extension

    logging.info(f"Media Server: Serving image download image_id={image_id}, name={download_name}")
    return send_file(
        abs_path,
        mimetype=mime_type,
        as_attachment=True,
        download_name=download_name,
        conditional=True,
    )


@app.route('/audio/<int:audio_id>/stream', methods=['GET'])
def stream_audio(audio_id: int):
    """Stream an audio file by ID for playback. Supports HTTP range requests for seeking."""
    import json

    cmd = ['python3', str(PROJECT_ROOT / 'download_client.py'), 'get_audio_info', '--id', str(audio_id)]

    acquired = _gateway_semaphore.acquire(timeout=10)
    if not acquired:
        logging.error("Gateway concurrency limit reached for audio stream request")
        return "Server busy, please retry", 503

    try:
        env = os.environ.copy()
        env['USER_TIER'] = 'admin'
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(PROJECT_ROOT),
            env=env,
        )
    finally:
        _gateway_semaphore.release()

    if result.returncode != 0 or not result.stdout:
        logging.warning(
            "download_client failed for audio_id=%s, rc=%s, stdout=%s, stderr=%s",
            audio_id,
            result.returncode,
            (result.stdout or "").strip(),
            (result.stderr or "").strip(),
        )
        return "Audio not found", 404

    try:
        resp = json.loads(result.stdout)
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON from download_client for audio_id={audio_id}: {result.stdout[:200]}")
        return "Internal error", 500

    if resp.get("status") != "ok":
        logging.info(f"Stream metadata error for audio_id={audio_id}: {resp.get('errors')}")
        return "Audio not found", 404

    audio_info = (resp.get("data") or {}).get("audio") or {}
    instances = audio_info.get("instances", [])
    if not instances:
        logging.info(f"No instances in metadata for audio_id={audio_id}")
        return "Audio not found", 404
    
    # Get full instance
    full_instance = None
    for instance in instances:
        if instance.get("instance_type") == "full":
            full_instance = instance
            break
    
    if not full_instance:
        full_instance = instances[0]
    
    rel_path = full_instance.get("file_path")
    if not rel_path:
        logging.info(f"No file_path in instance metadata for audio_id={audio_id}")
        return "Audio not found", 404

    base_path = Path(f"/srv/audio/{PROJECT_NAME}")
    abs_path = base_path / rel_path

    try:
        if not abs_path.exists():
            logging.info(f"Audio path missing on disk for audio_id={audio_id}: {abs_path}")
            return "Audio not found", 404
    except PermissionError:
        logging.warning(f"Permission denied checking audio existence for audio_id={audio_id}: {abs_path}")
        return "Permission denied", 403

    mime_type = full_instance.get("mime_type") or "audio/mpeg"

    logging.info(f"Media Server: Streaming audio audio_id={audio_id}")
    return send_file(
        abs_path,
        mimetype=mime_type,
        as_attachment=False,
        conditional=True,
    )


@app.route('/video/<int:video_id>/stream', methods=['GET'])
def stream_video(video_id: int):
    """Stream a video file by ID for playback. Supports HTTP range requests for seeking."""
    import json

    cmd = ['python3', str(PROJECT_ROOT / 'download_client.py'), 'get_video_info', '--id', str(video_id)]

    acquired = _gateway_semaphore.acquire(timeout=10)
    if not acquired:
        logging.error("Gateway concurrency limit reached for video stream request")
        return "Server busy, please retry", 503

    try:
        env = os.environ.copy()
        env['USER_TIER'] = 'admin'
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(PROJECT_ROOT),
            env=env,
        )
    finally:
        _gateway_semaphore.release()

    if result.returncode != 0 or not result.stdout:
        logging.warning(
            "download_client failed for video_id=%s, rc=%s, stdout=%s, stderr=%s",
            video_id,
            result.returncode,
            (result.stdout or "").strip(),
            (result.stderr or "").strip(),
        )
        return "Video not found", 404

    try:
        resp = json.loads(result.stdout)
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON from download_client for video_id={video_id}: {result.stdout[:200]}")
        return "Internal error", 500

    if resp.get("status") != "ok":
        logging.info(f"Stream metadata error for video_id={video_id}: {resp.get('errors')}")
        return "Video not found", 404

    video_info = (resp.get("data") or {}).get("video") or {}
    instances = video_info.get("instances", [])
    if not instances:
        logging.info(f"No instances in metadata for video_id={video_id}")
        return "Video not found", 404
    
    # Get full instance
    full_instance = None
    for instance in instances:
        if instance.get("instance_type") == "full":
            full_instance = instance
            break
    
    if not full_instance:
        full_instance = instances[0]
    
    rel_path = full_instance.get("file_path")
    if not rel_path:
        logging.info(f"No file_path in instance metadata for video_id={video_id}")
        return "Video not found", 404

    base_path = Path(f"/srv/video/{PROJECT_NAME}")
    abs_path = base_path / rel_path

    try:
        if not abs_path.exists():
            logging.info(f"Video path missing on disk for video_id={video_id}: {abs_path}")
            return "Video not found", 404
    except PermissionError:
        logging.warning(f"Permission denied checking video existence for video_id={video_id}: {abs_path}")
        return "Permission denied", 403

    mime_type = full_instance.get("mime_type") or "video/mp4"

    logging.info(f"Media Server: Streaming video video_id={video_id}")
    return send_file(
        abs_path,
        mimetype=mime_type,
        as_attachment=False,
        conditional=True,
    )


if __name__ == '__main__':
    # Run on all interfaces so Nginx can proxy
    port = int(os.getenv('PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=False)
