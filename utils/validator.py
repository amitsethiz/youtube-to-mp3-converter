"""
URL Validator Utility
Validates YouTube URLs and ensures security
"""

import re
import validators
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class URLValidator:
    """
    Validates YouTube URLs with security checks
    """
    
    # YouTube URL patterns
    YOUTUBE_PATTERNS = [
        r'^https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'^https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
        r'^https?://(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
        r'^https?://(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]+)',
        r'^https?://(?:m\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'^https?://(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]+)',
    ]
    
    # Blocked domains for security
    BLOCKED_DOMAINS = [
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
        '10.',
        '192.168.',
        '172.',
    ]
    
    # Maximum URL length
    MAX_URL_LENGTH = 2048
    
    # Minimum URL length
    MIN_URL_LENGTH = 20
    
    def __init__(self):
        """Initialize URL validator"""
        # Compile regex patterns for efficiency
        self.compiled_patterns = [re.compile(pattern) for pattern in self.YOUTUBE_PATTERNS]
    
    def is_valid_youtube_url(self, url):
        """
        Validate if the URL is a valid YouTube URL
        
        Args:
            url (str): The URL to validate
            
        Returns:
            bool: True if valid YouTube URL, False otherwise
        """
        try:
            # Check if URL is provided
            if not url or not isinstance(url, str):
                logger.warning("URL validation failed: URL is None or not a string")
                return False
            
            # Strip whitespace
            url = url.strip()
            
            # Check URL length
            if len(url) > self.MAX_URL_LENGTH:
                logger.warning(f"URL validation failed: URL too long ({len(url)} chars)")
                return False
            
            if len(url) < self.MIN_URL_LENGTH:
                logger.warning(f"URL validation failed: URL too short ({len(url)} chars)")
                return False
            
            # Basic URL validation using validators library
            if not validators.url(url):
                logger.warning("URL validation failed: Invalid URL format")
                return False
            
            # Parse URL
            parsed_url = urlparse(url)
            
            # Check if it's HTTP or HTTPS
            if parsed_url.scheme not in ['http', 'https']:
                logger.warning(f"URL validation failed: Invalid scheme '{parsed_url.scheme}'")
                return False
            
            # Check for blocked domains (security check)
            hostname = parsed_url.hostname.lower()
            for blocked in self.BLOCKED_DOMAINS:
                if hostname.startswith(blocked):
                    logger.warning(f"URL validation failed: Blocked domain '{hostname}'")
                    return False
            
            # Check for YouTube domain
            if not self._is_youtube_domain(hostname):
                logger.warning(f"URL validation failed: Not a YouTube domain '{hostname}'")
                return False
            
            # Check for YouTube video ID
            if not self._extract_video_id(url):
                logger.warning("URL validation failed: No valid video ID found")
                return False
            
            logger.info(f"URL validation successful: {url}")
            return True
            
        except Exception as e:
            logger.error(f"URL validation error: {str(e)}")
            return False
    
    def _is_youtube_domain(self, hostname):
        """
        Check if the hostname is a valid YouTube domain
        
        Args:
            hostname (str): The hostname to check
            
        Returns:
            bool: True if valid YouTube domain, False otherwise
        """
        valid_domains = [
            'youtube.com',
            'www.youtube.com',
            'm.youtube.com',
            'youtu.be',
            'www.youtu.be',
        ]
        
        return hostname in valid_domains
    
    def _extract_video_id(self, url):
        """
        Extract video ID from YouTube URL
        
        Args:
            url (str): The YouTube URL
            
        Returns:
            str or None: The video ID if found, None otherwise
        """
        try:
            # Try each pattern
            for pattern in self.compiled_patterns:
                match = pattern.match(url)
                if match:
                    video_id = match.group(1)
                    if self._is_valid_video_id(video_id):
                        return video_id
            
            return None
            
        except Exception as e:
            logger.error(f"Video ID extraction error: {str(e)}")
            return None
    
    def _is_valid_video_id(self, video_id):
        """
        Validate YouTube video ID format
        
        Args:
            video_id (str): The video ID to validate
            
        Returns:
            bool: True if valid video ID format, False otherwise
        """
        # YouTube video IDs are 11 characters, alphanumeric + underscore + dash
        if not video_id or len(video_id) != 11:
            return False
        
        # Check for valid characters
        if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
            return False
        
        return True
    
    def sanitize_url(self, url):
        """
        Sanitize URL by removing potentially harmful characters
        
        Args:
            url (str): The URL to sanitize
            
        Returns:
            str: Sanitized URL
        """
        try:
            if not url:
                return ""
            
            # Remove potential injection characters
            url = re.sub(r'[<>"\']', '', url)
            
            # Remove null bytes
            url = url.replace('\x00', '')
            
            # Strip whitespace
            url = url.strip()
            
            return url
            
        except Exception as e:
            logger.error(f"URL sanitization error: {str(e)}")
            return ""
    
    def get_video_info_from_url(self, url):
        """
        Extract video information from URL
        
        Args:
            url (str): The YouTube URL
            
        Returns:
            dict: Video information containing video_id, domain, etc.
        """
        try:
            if not self.is_valid_youtube_url(url):
                return None
            
            parsed_url = urlparse(url)
            video_id = self._extract_video_id(url)
            
            return {
                'video_id': video_id,
                'domain': parsed_url.netloc,
                'scheme': parsed_url.scheme,
                'is_mobile': 'm.youtube.com' in parsed_url.netloc,
                'url_type': self._get_url_type(url)
            }
            
        except Exception as e:
            logger.error(f"Video info extraction error: {str(e)}")
            return None
    
    def _get_url_type(self, url):
        """
        Determine the type of YouTube URL
        
        Args:
            url (str): The YouTube URL
            
        Returns:
            str: URL type (watch, embed, shorts, etc.)
        """
        if '/watch' in url:
            return 'watch'
        elif '/embed' in url:
            return 'embed'
        elif '/shorts' in url:
            return 'shorts'
        elif '/v/' in url:
            return 'direct'
        elif 'youtu.be' in url:
            return 'short'
        else:
            return 'unknown'
    
    def validate_url_safety(self, url):
        """
        Additional safety validation for URLs
        
        Args:
            url (str): The URL to validate
            
        Returns:
            dict: Safety check results
        """
        try:
            safety_results = {
                'is_safe': True,
                'warnings': [],
                'blocked_reasons': []
            }
            
            # Check for suspicious patterns
            suspicious_patterns = [
                r'javascript:',
                r'data:',
                r'file:',
                r'ftp:',
                r'chrome:',
                r'about:',
                r'view-source:',
            ]
            
            for pattern in suspicious_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    safety_results['is_safe'] = False
                    safety_results['blocked_reasons'].append(f'Suspicious pattern: {pattern}')
            
            # Check for IP addresses (should be blocked for security)
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', url):
                safety_results['is_safe'] = False
                safety_results['blocked_reasons'].append('IP address URL not allowed')
            
            # Check for port numbers (should be blocked for security)
            if ':' in url and '://' in url:
                try:
                    parsed = urlparse(url)
                    if parsed.port and parsed.port not in [80, 443]:
                        safety_results['is_safe'] = False
                        safety_results['blocked_reasons'].append(f'Non-standard port: {parsed.port}')
                except:
                    pass
            
            # Add warnings for potentially problematic URLs
            if len(url) > 1000:
                safety_results['warnings'].append('Very long URL')
            
            if url.count('?') > 5:
                safety_results['warnings'].append('URL has many query parameters')
            
            if url.count('&') > 20:
                safety_results['warnings'].append('URL has many parameters')
            
            logger.info(f"URL safety check completed: {safety_results}")
            return safety_results
            
        except Exception as e:
            logger.error(f"URL safety check error: {str(e)}")
            return {
                'is_safe': False,
                'warnings': ['Safety check failed'],
                'blocked_reasons': ['Internal error']
            }