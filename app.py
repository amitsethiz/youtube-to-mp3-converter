"""
YouTube to MP3 Converter Web Application
A Flask-based web application for converting YouTube videos to MP3 audio files.
"""

import os
import tempfile
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import validators
import uuid

# Import utility modules
from utils.converter import YouTubeConverter
from utils.validator import URLValidator
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS
CORS(app)

# Setup rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per day", "20 per hour", "5 per minute"]
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('youtube_converter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize utility classes
url_validator = URLValidator()
converter = YouTubeConverter()

# Global storage for conversion status
conversion_status = {}

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    """Handle file size too large errors."""
    return jsonify({'error': 'File too large. Maximum size is 50MB.'}), 413

@app.errorhandler(404)
def not_found_error(e):
    """Handle 404 errors."""
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    logger.error(f"Internal error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

@app.route('/')
def index():
    """Main page route."""
    return render_template('index.html')

@app.route('/validate_url', methods=['POST'])
@limiter.limit("10 per minute")
def validate_url():
    """
    Validate YouTube URL and return video information.
    """
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url = data['url'].strip()
        
        # Validate URL format
        if not url_validator.is_valid_youtube_url(url):
            return jsonify({'error': 'Invalid YouTube URL format'}), 400
        
        # Get video information
        video_info = converter.get_video_info(url)
        if not video_info:
            return jsonify({'error': 'Could not retrieve video information'}), 400
        
        return jsonify({
            'success': True,
            'title': video_info.get('title', 'Unknown Title'),
            'duration': video_info.get('duration', 0),
            'thumbnail': video_info.get('thumbnail', ''),
            'uploader': video_info.get('uploader', 'Unknown Uploader')
        })
        
    except Exception as e:
        logger.error(f"URL validation error: {str(e)}")
        return jsonify({'error': 'Failed to validate URL'}), 500

@app.route('/convert', methods=['POST'])
@limiter.limit("5 per minute")
def convert_video():
    """
    Convert YouTube video to MP3.
    """
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url = data['url'].strip()
        quality = data.get('quality', '192k')
        v_format = data.get('format', 'mp3')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        # Validate URL
        if not url_validator.is_valid_youtube_url(url):
            return jsonify({'error': 'Invalid YouTube URL format'}), 400
        
        # Generate unique ID for this conversion
        conversion_id = str(uuid.uuid4())
        
        # Store initial status
        conversion_status[conversion_id] = {
            'status': 'starting',
            'progress': 0,
            'message': 'Initializing process...'
        }
        
        # Start conversion process (synchronous for now)
        try:
            # Update status
            conversion_status[conversion_id].update({
                'status': 'downloading',
                'progress': 10,
                'message': 'Processing...'
            })
            
            # Download and convert
            if v_format == 'mp4':
                output_path = converter.convert_to_mp4(url, quality, conversion_status[conversion_id])
            else:
                output_path = converter.convert_to_mp3(url, quality, conversion_status[conversion_id], start_time=start_time, end_time=end_time)
            
            if output_path and os.path.exists(output_path):
                # Update status to success
                conversion_status[conversion_id].update({
                    'status': 'completed',
                    'progress': 100,
                    'message': 'Conversion completed successfully!',
                    'file_path': output_path,
                    'file_name': os.path.basename(output_path)
                })
                
                return jsonify({
                    'success': True,
                    'conversion_id': conversion_id,
                    'message': 'Conversion completed successfully!'
                })
            else:
                raise Exception("Conversion failed - no output file")
                
        except Exception as conversion_error:
            # Update status to error
            conversion_status[conversion_id].update({
                'status': 'error',
                'progress': 0,
                'message': f'Conversion failed: {str(conversion_error)}'
            })
            
            logger.error(f"Conversion error for {conversion_id}: {str(conversion_error)}")
            return jsonify({'error': f'Conversion failed: {str(conversion_error)}'}), 500
            
    except Exception as e:
        logger.error(f"Conversion route error: {str(e)}")
        return jsonify({'error': 'Failed to process conversion request'}), 500

@app.route('/status/<conversion_id>', methods=['GET'])
@limiter.limit("20 per minute")
def get_conversion_status(conversion_id):
    """
    Get conversion status for a specific conversion ID.
    """
    try:
        if conversion_id not in conversion_status:
            return jsonify({'error': 'Conversion ID not found'}), 404
        
        status = conversion_status[conversion_id]
        
        # Clean up completed conversions after 1 hour
        if status['status'] == 'completed':
            # Keep the file available for download for 1 hour
            # (In a production app, you might want to store this in a database)
            pass
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return jsonify({'error': 'Failed to get conversion status'}), 500

@app.route('/download/<conversion_id>', methods=['GET'])
@limiter.limit("10 per minute")
def download_file(conversion_id):
    """
    Download the converted MP3 file.
    """
    try:
        if conversion_id not in conversion_status:
            return jsonify({'error': 'Conversion ID not found'}), 404
        
        status = conversion_status[conversion_id]
        
        if status['status'] != 'completed' or 'file_path' not in status:
            return jsonify({'error': 'File not ready for download'}), 400
        
        file_path = status['file_path']
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File no longer exists'}), 404
        
        # Clean up filename
        original_file_name = status.get('file_name', '')
        ext = '.mp4' if original_file_name.endswith('.mp4') else '.mp3'
        file_name = secure_filename(original_file_name or f'conversion_{conversion_id}{ext}')
        mimetype = 'video/mp4' if ext == '.mp4' else 'audio/mpeg'
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_name,
            mimetype=mimetype
        )
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': 'Failed to download file'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@app.before_request
def before_request():
    """Execute before each request."""
    # Add security headers
    request.headers.environ['HTTP_SECURITY_HEADERS'] = '1'
    request.headers.environ['HTTP_CONTENT_SECURITY_POLICY'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; media-src 'self'; connect-src 'self';"

@app.after_request
def after_request(response):
    """Execute after each request."""
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Add CORS headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    
    return response

# Cleanup function to remove old temporary files
def cleanup_temp_files():
    """Remove temporary files older than 1 hour."""
    try:
        temp_dir = app.config['TEMP_DIR']
        current_time = datetime.now().timestamp()
        
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path):
                file_time = os.path.getmtime(file_path)
                if current_time - file_time > 3600:  # 1 hour
                    os.remove(file_path)
                    logger.info(f"Cleaned up old file: {filename}")
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")

if __name__ == '__main__':
    # Create temp directory if it doesn't exist
    os.makedirs(app.config['TEMP_DIR'], exist_ok=True)
    os.makedirs(app.config['DOWNLOADS_DIR'], exist_ok=True)
    
    # Start cleanup scheduler (in production, use a proper scheduler)
    import threading
    cleanup_thread = threading.Thread(target=cleanup_temp_files, daemon=True)
    cleanup_thread.start()
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=app.config['DEBUG'],
        threaded=True
    )