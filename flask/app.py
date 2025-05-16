import os
import logging
from flask import Flask, render_template, request, jsonify, send_file, session
from pytubefix import YouTube
import tempfile
import urllib.parse
import re

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

def is_valid_youtube_url(url):
    """Check if the URL is a valid YouTube URL."""
    # Regular expression pattern for YouTube URLs
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    
    youtube_regex_match = re.match(youtube_regex, url)
    if youtube_regex_match:
        return True
    return False

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/fetch_video_info', methods=['POST'])
def fetch_video_info():
    """Fetch video information from a YouTube URL."""
    data = request.get_json()
    url = data.get('url', '')
    
    # Validate URL format
    if not is_valid_youtube_url(url):
        return jsonify({
            'success': False,
            'message': 'Invalid YouTube URL format. Please provide a valid YouTube URL.'
        }), 400
    
    try:
        # Get video information using PyTubeFix
        yt = YouTube(url)
        
        # Get available streams (excluding audio-only)
        streams = yt.streams.filter(progressive=True)
        
        # Prepare stream options for the frontend
        stream_options = []
        for stream in streams:
            stream_options.append({
                'itag': stream.itag,
                'resolution': stream.resolution,
                'fps': stream.fps,
                'mime_type': stream.mime_type,
                'size_mb': round(stream.filesize / (1024 * 1024), 2)
            })
        
        # Store video URL in session for later use when downloading
        session['video_url'] = url
        
        return jsonify({
            'success': True,
            'title': yt.title,
            'thumbnail': yt.thumbnail_url,
            'duration': yt.length,
            'author': yt.author,
            'streams': stream_options
        })
    except Exception as e:
        logger.exception(f"Error fetching video information: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error fetching video information: {str(e)}"
        }), 500

@app.route('/download', methods=['POST'])
def download_video():
    """Download a YouTube video in the specified format."""
    data = request.get_json()
    itag = data.get('itag')
    
    # Get video URL from session
    url = session.get('video_url')
    if not url:
        return jsonify({
            'success': False,
            'message': 'Video URL not found in session. Please fetch video info first.'
        }), 400
    
    try:
        yt = YouTube(url)
        stream = yt.streams.get_by_itag(itag)
        
        if not stream:
            return jsonify({
                'success': False,
                'message': 'Selected video format not available.'
            }), 400
        
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        # Clean filename to avoid issues with special characters
        safe_filename = "".join([c for c in yt.title if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
        filename = f"{safe_filename}_{stream.resolution}.mp4"
        file_path = os.path.join(temp_dir, filename)
        
        # Download the video
        stream.download(output_path=temp_dir, filename=filename)
        
        # Return download link
        return jsonify({
            'success': True,
            'download_path': f"/download_file?path={urllib.parse.quote(file_path)}&filename={urllib.parse.quote(filename)}"
        })
    except Exception as e:
        logger.exception(f"Error downloading video: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error downloading video: {str(e)}"
        }), 500

@app.route('/download_file', methods=['GET'])
def download_file():
    """Send the downloaded file to the user."""
    file_path = request.args.get('path')
    filename = request.args.get('filename')
    
    if not file_path or not filename:
        return "Missing file path or filename", 400
    
    try:
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        logger.exception(f"Error sending file: {str(e)}")
        return f"Error sending file: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
