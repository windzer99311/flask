import os
import logging
import tempfile
import urllib.parse
import re
from flask import Flask, request, jsonify, send_file, session, Response
from pytubefix import YouTube

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
    """Render the main page with inline HTML."""
    html = """
    <!DOCTYPE html>
    <html lang="en" data-bs-theme="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>YouTube Video Downloader</title>
        <!-- Bootstrap CSS (Replit Theme) -->
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <!-- Font Awesome -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.3.0/css/all.min.css">
        <style>
            /* Custom styles for YouTube downloader */
            .video-container {
                border-radius: 10px;
                transition: all 0.3s ease;
            }

            .thumbnail-container {
                position: relative;
                overflow: hidden;
                border-radius: 8px;
            }

            .thumbnail-container img {
                width: 100%;
                transition: transform 0.3s ease;
            }

            .thumbnail-container:hover img {
                transform: scale(1.05);
            }

            .stream-option {
                cursor: pointer;
                transition: all 0.2s ease;
            }

            .stream-option:hover {
                transform: translateY(-2px);
            }

            .stream-option.selected {
                border-color: var(--bs-primary) !important;
            }

            .progress-container {
                height: 5px;
                margin-top: 10px;
            }

            /* Animation for loading state */
            @keyframes pulse {
                0% { opacity: 0.6; }
                50% { opacity: 1; }
                100% { opacity: 0.6; }
            }

            .loading {
                animation: pulse 1.5s infinite;
            }

            /* Responsive adjustments */
            @media (max-width: 768px) {
                .video-info-container {
                    flex-direction: column;
                }

                .thumbnail-container {
                    max-width: 100%;
                    margin-bottom: 15px;
                }
            }
        </style>
    </head>
    <body>
        <header class="bg-dark py-3">
            <div class="container">
                <div class="d-flex align-items-center justify-content-between">
                    <h1 class="h4 mb-0 text-light">
                        <i class="fab fa-youtube text-danger me-2"></i>
                        YouTube Video Downloader
                    </h1>
                </div>
            </div>
        </header>

        <main class="container py-4">
            <div class="row justify-content-center">
                <div class="col-lg-10">
                    <!-- Alert Container -->
                    <div id="alert-container" class="mb-3"></div>

                    <!-- URL Input Form -->
                    <div class="card mb-4">
                        <div class="card-body">
                            <h2 class="card-title h5 mb-3">
                                <i class="fas fa-link text-info me-2"></i> Enter YouTube URL
                            </h2>
                            <form id="url-form">
                                <div class="input-group">
                                    <input type="text" id="video-url" class="form-control" placeholder="https://www.youtube.com/watch?v=..." required>
                                    <button type="submit" id="fetch-button" class="btn btn-primary">
                                        <i class="fas fa-search me-1"></i> Fetch Video Info
                                    </button>
                                </div>
                                <div class="form-text">Enter a valid YouTube video URL to download</div>
                            </form>
                        </div>
                    </div>

                    <!-- Video Information Container (Initially Hidden) -->
                    <div id="video-info-container" class="d-none">
                        <div class="card mb-4">
                            <div class="card-body">
                                <h2 class="card-title h5 mb-3">
                                    <i class="fas fa-video text-success me-2"></i> Video Information
                                </h2>

                                <div class="d-flex flex-wrap video-info-container">
                                    <div class="thumbnail-container me-3 mb-3" style="width: 200px;">
                                        <img id="video-thumbnail" src="" alt="Video Thumbnail" class="img-fluid rounded">
                                    </div>

                                    <div class="flex-grow-1">
                                        <h3 id="video-title" class="h5 mb-2"></h3>

                                        <div class="mb-2">
                                            <span class="badge bg-secondary me-2">
                                                <i class="fas fa-user me-1"></i> <span id="video-author"></span>
                                            </span>
                                            <span class="badge bg-secondary">
                                                <i class="fas fa-clock me-1"></i> <span id="video-duration"></span>
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Download Options -->
                        <div class="card mb-4">
                            <div class="card-body">
                                <h2 class="card-title h5 mb-3">
                                    <i class="fas fa-download text-primary me-2"></i> Download Options
                                </h2>

                                <p class="text-muted mb-3">Select a format to download:</p>

                                <div id="stream-options" class="mb-3"></div>

                                <!-- Loading Indicator -->
                                <div id="loading-indicator" class="d-none mb-3">
                                    <div class="progress progress-container">
                                        <div class="progress-bar progress-bar-striped progress-bar-animated w-100" role="progressbar" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100"></div>
                                    </div>
                                    <p class="text-center text-muted mt-2"><small>Preparing your download... this may take a moment</small></p>
                                </div>

                                <button id="download-button" class="btn btn-success w-100" disabled>
                                    <i class="fas fa-download me-1"></i> Download
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Instructions Card -->
                    <div class="card">
                        <div class="card-body">
                            <h2 class="card-title h5 mb-3">
                                <i class="fas fa-info-circle text-info me-2"></i> How to use
                            </h2>
                            <ol class="mb-0">
                                <li>Paste a YouTube video URL in the input field above</li>
                                <li>Click "Fetch Video Info" to load available download options</li>
                                <li>Select your preferred video quality</li>
                                <li>Click the "Download" button to start downloading</li>
                            </ol>
                        </div>
                    </div>
                </div>
            </div>
        </main>

        <footer class="bg-dark py-3 mt-4">
            <div class="container text-center text-muted">
                <p class="mb-0">Built with Flask and PyTubeFix | <i class="fas fa-code"></i> with <i class="fas fa-heart text-danger"></i></p>
            </div>
        </footer>

        <!-- Bootstrap JS Bundle with Popper -->
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

        <!-- Custom JS -->
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                // DOM Elements
                const urlForm = document.getElementById('url-form');
                const urlInput = document.getElementById('video-url');
                const fetchButton = document.getElementById('fetch-button');
                const videoInfoContainer = document.getElementById('video-info-container');
                const videoTitle = document.getElementById('video-title');
                const videoThumbnail = document.getElementById('video-thumbnail');
                const videoDuration = document.getElementById('video-duration');
                const videoAuthor = document.getElementById('video-author');
                const streamOptions = document.getElementById('stream-options');
                const downloadButton = document.getElementById('download-button');
                const alertContainer = document.getElementById('alert-container');
                const downloadProgress = document.getElementById('download-progress');
                const loadingIndicator = document.getElementById('loading-indicator');

                let selectedItag = null;

                // Event Listeners
                urlForm.addEventListener('submit', fetchVideoInfo);

                // Format duration from seconds to MM:SS format
                function formatDuration(seconds) {
                    const minutes = Math.floor(seconds / 60);
                    const remainingSeconds = seconds % 60;
                    return `${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
                }

                // Show alert message
                function showAlert(message, type = 'danger') {
                    alertContainer.innerHTML = `
                        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                            ${message}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>
                    `;

                    // Auto dismiss after 5 seconds
                    setTimeout(() => {
                        const alert = alertContainer.querySelector('.alert');
                        if (alert) {
                            const bsAlert = new bootstrap.Alert(alert);
                            bsAlert.close();
                        }
                    }, 5000);
                }

                // Fetch video information
                function fetchVideoInfo(e) {
                    e.preventDefault();

                    const url = urlInput.value.trim();
                    if (!url) {
                        showAlert('Please enter a YouTube URL');
                        return;
                    }

                    // Show loading state
                    fetchButton.disabled = true;
                    fetchButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Fetching...';
                    videoInfoContainer.classList.add('d-none');
                    alertContainer.innerHTML = '';

                    // API request
                    fetch('/fetch_video_info', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ url: url }),
                    })
                    .then(response => response.json())
                    .then(data => {
                        fetchButton.disabled = false;
                        fetchButton.innerHTML = 'Fetch Video Info';

                        if (data.success) {
                            displayVideoInfo(data);
                        } else {
                            showAlert(data.message);
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        fetchButton.disabled = false;
                        fetchButton.innerHTML = 'Fetch Video Info';
                        showAlert('An error occurred. Please try again.');
                    });
                }

                // Display video information
                function displayVideoInfo(data) {
                    videoTitle.textContent = data.title;
                    videoThumbnail.src = data.thumbnail;
                    videoDuration.textContent = formatDuration(data.duration);
                    videoAuthor.textContent = data.author;

                    // Display stream options
                    streamOptions.innerHTML = '';
                    data.streams.forEach(stream => {
                        const streamOption = document.createElement('div');
                        streamOption.className = 'stream-option card mb-2 border';
                        streamOption.innerHTML = `
                            <div class="card-body p-3">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 class="mb-0">${stream.resolution}</h6>
                                        <small class="text-muted">${stream.mime_type} | ${stream.fps}fps</small>
                                    </div>
                                    <div>
                                        <span class="badge bg-info">${stream.size_mb} MB</span>
                                    </div>
                                </div>
                            </div>
                        `;

                        streamOption.dataset.itag = stream.itag;
                        streamOption.addEventListener('click', () => {
                            document.querySelectorAll('.stream-option').forEach(opt => {
                                opt.classList.remove('selected');
                                opt.classList.remove('border-primary');
                            });
                            streamOption.classList.add('selected');
                            streamOption.classList.add('border-primary');
                            selectedItag = stream.itag;
                            downloadButton.disabled = false;
                        });

                        streamOptions.appendChild(streamOption);
                    });

                    // Show video info container
                    videoInfoContainer.classList.remove('d-none');
                    downloadButton.disabled = true;

                    // Set up download button
                    downloadButton.onclick = downloadVideo;
                }

                // Download video
                function downloadVideo() {
                    if (!selectedItag) {
                        showAlert('Please select a download option');
                        return;
                    }

                    // Show loading state
                    downloadButton.disabled = true;
                    downloadButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Preparing download...';

                    // Show progress indicator
                    loadingIndicator.classList.remove('d-none');

                    // API request
                    fetch('/download', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ itag: selectedItag }),
                    })
                    .then(response => response.json())
                    .then(data => {
                        downloadButton.disabled = false;
                        downloadButton.innerHTML = 'Download';
                        loadingIndicator.classList.add('d-none');

                        if (data.success) {
                            // Create download link and click it
                            window.location.href = data.download_path;
                            showAlert('Download started!', 'success');
                        } else {
                            showAlert(data.message);
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        downloadButton.disabled = false;
                        downloadButton.innerHTML = 'Download';
                        loadingIndicator.classList.add('d-none');
                        showAlert('An error occurred during download. Please try again.');
                    });
                }
            });
        </script>
    </body>
    </html>
    """
    return Response(html, mimetype='text/html')


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
        yt = YouTube(url, use_po_token=True)

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
        yt = YouTube(url, use_po_token=True)
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

