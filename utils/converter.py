"""
YouTube Converter Utility
Handles downloading and conversion of YouTube videos to MP3
"""

import os
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path
from urllib.parse import urlparse
import yt_dlp
import re

# Use imageio-ffmpeg bundled binary (works on Render free tier without system install)
try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_PATH = 'ffmpeg'  # Fallback to system ffmpeg

logger = logging.getLogger(__name__)

class YouTubeConverter:
    """
    Handles YouTube video downloading and MP3 conversion
    """
    
    def __init__(self, temp_dir=None, downloads_dir=None):
        """
        Initialize the converter
        
        Args:
            temp_dir (str): Directory for temporary files
            downloads_dir (str): Directory for final downloads
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.downloads_dir = downloads_dir or os.path.join(os.getcwd(), 'downloads')
        
        # Create directories if they don't exist
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.downloads_dir, exist_ok=True)
        
        # yt-dlp base options (used for info extraction and download)
        self.ydl_base_opts = {
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            # android_vr client bypasses PO Token requirement (avoids HTTP 403)
            'extractor_args': {'youtube': {'player_client': ['android_vr']}},
            # Point yt-dlp to the bundled imageio-ffmpeg binary
            'ffmpeg_location': FFMPEG_PATH,
        }
    
    def get_video_info(self, url):
        """
        Get video information without downloading
        
        Args:
            url (str): YouTube video URL
            
        Returns:
            dict: Video information or None if error
        """
        try:
            opts = self.ydl_base_opts.copy()

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return None
                
                # Extract relevant information
                video_info = {
                    'title': info.get('title', 'Unknown Title'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', 'Unknown Uploader'),
                    'view_count': info.get('view_count', 0),
                    'upload_date': info.get('upload_date', ''),
                    'description': info.get('description', '')[:200] + '...' if info.get('description') else '',
                    'webpage_url': info.get('webpage_url', url)
                }
                
                return video_info
                
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            return None
    
    def convert_to_mp3(self, url, quality='192k', status_callback=None, start_time=None, end_time=None):
        """
        Convert YouTube video to MP3 and optionally crop it.
        
        Args:
            url (str): YouTube video URL
            quality (str): Audio quality (128k, 192k, 320k)
            status_callback (dict): Status dictionary to update progress
            start_time (int): Start cropping time in seconds
            end_time (int): End cropping time in seconds
            
        Returns:
            str: Path to converted MP3 file or None if error
        """
        try:
            if status_callback:
                status_callback['status'] = 'downloading'
                status_callback['progress'] = 20
                status_callback['message'] = 'Fetching video information...'

            # Strip the bitrate suffix to get numeric quality (e.g. "192k" -> "192")
            numeric_quality = quality.rstrip('k').rstrip('K')

            # Output template: save directly into downloads dir as .mp3
            # yt-dlp postprocessor will rename the extension automatically
            outtmpl = os.path.join(self.downloads_dir, f'%(title)s_{quality}.%(ext)s')

            opts = self.ydl_base_opts.copy()
            opts.update({
                'format': 'bestaudio/best',
                'outtmpl': outtmpl,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': numeric_quality,
                }],
            })

            downloaded_path = [None]  # capture final path via hook

            def progress_hook(d):
                if d['status'] == 'downloading' and status_callback:
                    status_callback['progress'] = 50
                    status_callback['message'] = 'Downloading audio...'
                elif d['status'] == 'finished':
                    # d['filename'] is the pre-conversion file; MP3 will have .mp3 ext
                    downloaded_path[0] = d['filename']
                    if status_callback:
                        status_callback['status'] = 'converting'
                        status_callback['progress'] = 80
                        status_callback['message'] = 'Converting to MP3...'

            opts['progress_hooks'] = [progress_hook]

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise Exception("Could not retrieve video information")

            # Resolve the final .mp3 path
            if downloaded_path[0]:
                base = os.path.splitext(downloaded_path[0])[0]
                mp3_file = base + '.mp3'
            else:
                # Fallback: find the newest .mp3 in downloads dir
                mp3_files = sorted(
                    [os.path.join(self.downloads_dir, f)
                     for f in os.listdir(self.downloads_dir) if f.endswith('.mp3')],
                    key=os.path.getmtime, reverse=True
                )
                mp3_file = mp3_files[0] if mp3_files else None

            if not mp3_file or not os.path.exists(mp3_file):
                raise Exception("Conversion failed — MP3 file not found after processing")

            # Apply Cropping if provided
            if start_time is not None or end_time is not None:
                if status_callback:
                    status_callback['status'] = 'converting'
                    status_callback['message'] = 'Cropping audio...'
                
                cropped_file = os.path.join(self.downloads_dir, f'cropped_{os.path.basename(mp3_file)}')
                ffmpeg_cmd = [FFMPEG_PATH, '-y', '-i', mp3_file]
                if start_time is not None:
                    ffmpeg_cmd.extend(['-ss', str(start_time)])
                if end_time is not None:
                    ffmpeg_cmd.extend(['-to', str(end_time)])
                ffmpeg_cmd.extend(['-c', 'copy', cropped_file])
                
                try:
                    subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
                    mp3_file = cropped_file
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to crop: {e.stderr}")

            if status_callback:
                status_callback['status'] = 'completed'
                status_callback['progress'] = 100
                status_callback['message'] = 'Conversion completed successfully!'

            logger.info(f"Successfully converted to MP3: {mp3_file}")
            return mp3_file

        except Exception as e:
            logger.error(f"Conversion error: {str(e)}")
            if status_callback:
                status_callback['status'] = 'error'
                status_callback['progress'] = 0
                status_callback['message'] = f'Conversion failed: {str(e)}'
            return None
            
    def convert_to_mp4(self, url, quality='720p', status_callback=None):
        """
        Download YouTube video as MP4
        
        Args:
            url (str): YouTube video URL
            quality (str): Video quality (360p, 720p, 1080p)
            status_callback (dict): Status dictionary to update progress
            
        Returns:
            str: Path to downloaded MP4 file or None if error
        """
        try:
            if status_callback:
                status_callback['status'] = 'downloading'
                status_callback['progress'] = 20
                status_callback['message'] = 'Fetching video information...'

            q_num = quality.replace('p', '')
            format_str = f'bestvideo[ext=mp4][height<={q_num}]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            outtmpl = os.path.join(self.downloads_dir, f'%(title)s_{quality}.%(ext)s')

            opts = self.ydl_base_opts.copy()
            opts.update({
                'format': format_str,
                'outtmpl': outtmpl,
                'merge_output_format': 'mp4',
            })

            downloaded_path = [None]

            def progress_hook(d):
                if d['status'] == 'downloading' and status_callback:
                    status_callback['progress'] = 50
                    status_callback['message'] = 'Downloading video...'
                elif d['status'] == 'finished':
                    info_dict = d.get('info_dict', {})
                    downloaded_path[0] = info_dict.get('_filename') or d.get('filename')
                    if status_callback:
                        status_callback['status'] = 'converting'
                        status_callback['progress'] = 80
                        status_callback['message'] = 'Processing MP4...'

            opts['progress_hooks'] = [progress_hook]

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise Exception("Could not retrieve video information")

            if downloaded_path[0]:
                base = os.path.splitext(downloaded_path[0])[0]
                mp4_file = base + '.mp4'
            else:
                mp4_files = sorted(
                    [os.path.join(self.downloads_dir, f)
                     for f in os.listdir(self.downloads_dir) if f.endswith('.mp4')],
                    key=os.path.getmtime, reverse=True
                )
                mp4_file = mp4_files[0] if mp4_files else None

            if not mp4_file or not os.path.exists(mp4_file):
                raise Exception("Conversion failed — MP4 file not found after processing")

            if status_callback:
                status_callback['status'] = 'completed'
                status_callback['progress'] = 100
                status_callback['message'] = 'Download completed successfully!'

            logger.info(f"Successfully downloaded MP4: {mp4_file}")
            return mp4_file

        except Exception as e:
            logger.error(f"Conversion error: {str(e)}")
            if status_callback:
                status_callback['status'] = 'error'
                status_callback['progress'] = 0
                status_callback['message'] = f'Download failed: {str(e)}'
            return None
    
    def _sanitize_filename(self, filename):
        """
        Sanitize filename by removing invalid characters
        
        Args:
            filename (str): Original filename
            
        Returns:
            str: Sanitized filename
        """
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'[^\w\s\-\.]', '', filename)  # Fixed: escape the dash
        filename = re.sub(r'\s+', '_', filename)
        filename = filename[:100]  # Limit length
        
        return filename or 'youtube_audio'
    
    def estimate_file_size(self, duration, quality):
        """
        Estimate file size based on duration and quality
        
        Args:
            duration (int): Duration in seconds
            quality (str): Audio quality
            
        Returns:
            int: Estimated file size in bytes
        """
        # Bitrate to bytes per second calculation
        bitrates = {
            '128k': 128000,
            '192k': 192000,
            '320k': 320000
        }
        
        bitrate = bitrates.get(quality, 192000)
        
        # Estimate file size (duration * bitrate / 8)
        estimated_size = (duration * bitrate) // 8
        
        return estimated_size
    
    def format_file_size(self, size_bytes):
        """
        Format file size in human readable format
        
        Args:
            size_bytes (int): Size in bytes
            
        Returns:
            str: Formatted file size
        """
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def cleanup_temp_files(self):
        """
        Clean up temporary files
        """
        try:
            if os.path.exists(self.temp_dir):
                for filename in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
    
    def check_dependencies(self):
        """
        Check if required dependencies are available
        
        Returns:
            dict: Status of dependencies
        """
        status = {
            'ffmpeg': False,
            'yt_dlp': False,
            'temp_dir': os.path.exists(self.temp_dir),
            'downloads_dir': os.path.exists(self.downloads_dir)
        }
        
        # Check FFmpeg
        try:
            result = subprocess.run([FFMPEG_PATH, '-version'],
                                  capture_output=True, text=True, timeout=10)
            status['ffmpeg'] = result.returncode == 0
        except Exception:
            status['ffmpeg'] = False
        
        # Check yt-dlp
        try:
            import yt_dlp
            status['yt_dlp'] = True
        except ImportError:
            status['yt_dlp'] = False
        
        return status