import os
import sys
import re
import time
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.common import read_yaml, create_directories, get_size, get_env_var

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('errors.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class YouTubeDataExtractor:
    """
    Extracts comments from YouTube videos using YouTube Data API v3.
    
    Features:
    - Fetch comments by video ID
    - Handle pagination (nextPageToken)
    - Rate limiting with sleep between requests
    - Quota usage tracking
    - Error handling and retries
    """
    
    # YouTube API quota costs
    QUOTA_COST_SEARCH = 100      # search().list()
    QUOTA_COST_COMMENTS = 1      # commentThreads().list()
    QUOTA_COST_VIDEO = 1         # videos().list()
    
    def __init__(self, config_path: Path = None):
        """
        Initialize YouTubeDataExtractor.
        
        Args:
            config_path: Path to params.yaml. If None, uses default path.
        """
        self.project_root = Path(__file__).resolve().parent.parent.parent
        
        if config_path is None:
            config_path = self.project_root / "params.yaml"
        
        self.config = read_yaml(config_path)
        self.youtube_config = self.config.get("youtube_data", {})
        
        # Setup directories
        self.raw_data_path = self.project_root / "data" / "raw"
        create_directories([self.raw_data_path])
        
        # API configuration
        self.api_key = get_env_var(self.youtube_config.get("api_key_env", "YOUTUBE_API_KEY"))
        self.max_comments_per_video = self.youtube_config.get("max_comments_per_video", 1000)
        self.max_videos = self.youtube_config.get("max_videos", 5)
        self.video_ids = self.youtube_config.get("video_ids", [])
        
        # Quota tracking
        self.quota_used = 0
        self.max_quota = 10000  # Free tier: 10,000 units/day
        
        # Initialize YouTube API client
        self.youtube = self._build_youtube_client()
        
        logger.info(f"YouTubeDataExtractor initialized. Project root: {self.project_root}")
        logger.info(f"Max comments per video: {self.max_comments_per_video}")
        logger.info(f"Max videos: {self.max_videos}")

    def _build_youtube_client(self):
        """Build and return the YouTube API client."""
        if not self.api_key:
            raise ValueError(
                "YouTube API key not found. "
                f"Please set {self.youtube_config.get('api_key_env', 'YOUTUBE_API_KEY')} in your .env file."
            )
        
        try:
            youtube = build('youtube', 'v3', developerKey=self.api_key)
            logger.info("YouTube API client initialized successfully")
            return youtube
        except Exception as e:
            logger.error(f"Failed to initialize YouTube API client: {e}")
            raise e

    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from various YouTube URL formats.
        
        Args:
            url: YouTube video URL.
            
        Returns:
            Video ID string or None if not found.
        """
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
            r'^([a-zA-Z0-9_-]{11})$'  # Direct video ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        logger.warning(f"Could not extract video ID from URL: {url}")
        return None

    def get_video_details(self, video_id: str) -> Dict:
        """
        Get video title and details.
        
        Args:
            video_id: YouTube video ID.
            
        Returns:
            Dictionary with video details.
        """
        try:
            request = self.youtube.videos().list(
                part='snippet,statistics',
                id=video_id
            )
            response = request.execute()
            self.quota_used += self.QUOTA_COST_VIDEO
            
            if not response['items']:
                logger.warning(f"Video not found: {video_id}")
                return {}
            
            video = response['items'][0]
            return {
                'video_id': video_id,
                'title': video['snippet']['title'],
                'channel': video['snippet']['channelTitle'],
                'published_at': video['snippet']['publishedAt'],
                'view_count': int(video['statistics'].get('viewCount', 0)),
                'like_count': int(video['statistics'].get('likeCount', 0)),
                'comment_count': int(video['statistics'].get('commentCount', 0))
            }
            
        except HttpError as e:
            logger.error(f"HTTP error fetching video details for {video_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching video details for {video_id}: {e}")
            raise


    def fetch_comments(self, video_id: str, max_results: int = None) -> List[Dict]:
        """
        Fetch comments for a specific video.
        
        Args:
            video_id: YouTube video ID.
            max_results: Maximum comments to fetch. Defaults to config value.
            
        Returns:
            List of comment dictionaries.
        """
        if max_results is None:
            max_results = self.max_comments_per_video
        
        logger.info(f"Fetching comments for video: {video_id} (max: {max_results})")
        
        comments = []
        page_token = None
        pages_fetched = 0
        max_pages = (max_results // 100) + 2  # 100 comments per page + buffer
        
        try:
            while len(comments) < max_results and pages_fetched < max_pages:
                # Check quota
                if self.quota_used >= self.max_quota:
                    logger.warning("YouTube API quota exceeded! Stopping.")
                    break
                
                request = self.youtube.commentThreads().list(
                    part='snippet,replies',
                    videoId=video_id,
                    maxResults=min(100, max_results - len(comments)),  # API max is 100 per request
                    pageToken=page_token,
                    textFormat='plainText',
                    order='relevance'  # Get top comments first
                )
                
                response = request.execute()
                self.quota_used += self.QUOTA_COST_COMMENTS
                pages_fetched += 1
                
                for item in response['items']:
                    snippet = item['snippet']['topLevelComment']['snippet']
                    
                    comment = {
                        'comment_id': item['id'],
                        'video_id': video_id,
                        'text': snippet.get('textDisplay', ''),
                        'author': snippet.get('authorDisplayName', ''),
                        'like_count': snippet.get('likeCount', 0),
                        'published_at': snippet.get('publishedAt', ''),
                        'reply_count': item['snippet'].get('totalReplyCount', 0)
                    }
                    comments.append(comment)
                    
                    # Check if we've reached max results
                    if len(comments) >= max_results:
                        break
                
                # Get next page token
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
                
                # Rate limiting: sleep briefly between requests
                time.sleep(0.5)
            
            logger.info(f"Fetched {len(comments)} comments for video {video_id}")
            logger.info(f"Total quota used: {self.quota_used}")
            return comments
            
        except HttpError as e:
            if e.resp.status == 403 and 'quotaExceeded' in str(e):
                logger.error("YouTube API quota exceeded!")
            elif e.resp.status == 404:
                logger.error(f"Video not found or comments disabled: {video_id}")
            else:
                logger.error(f"HTTP error fetching comments for {video_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching comments for {video_id}: {e}")
            raise


    def fetch_multiple_videos(self, video_ids: List[str] = None) -> pd.DataFrame:
        """
        Fetch comments from multiple videos.
        
        Args:
            video_ids: List of video IDs. Defaults to config video_ids.
            
        Returns:
            DataFrame with all comments.
        """
        if video_ids is None:
            video_ids = self.video_ids
        
        if not video_ids:
            logger.warning("No video IDs provided!")
            return pd.DataFrame()
        
        all_comments = []
        
        for i, video_id in enumerate(video_ids[:self.max_videos]):
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing video {i+1}/{len(video_ids[:self.max_videos])}: {video_id}")
            logger.info(f"{'='*60}")
            
            # Get video details
            video_details = self.get_video_details(video_id)
            if video_details:
                logger.info(f"Title: {video_details.get('title', 'N/A')}")
                logger.info(f"Comments available: {video_details.get('comment_count', 'N/A')}")
            
            # Fetch comments
            comments = self.fetch_comments(video_id)
            all_comments.extend(comments)
            
            # Sleep between videos to be respectful to API
            if i < len(video_ids[:self.max_videos]) - 1:
                time.sleep(1)
        
        # Create DataFrame
        df = pd.DataFrame(all_comments)
        
        if not df.empty:
            logger.info(f"\n{'='*60}")
            logger.info(f"Total comments fetched: {len(df)}")
            logger.info(f"From {df['video_id'].nunique()} videos")
            logger.info(f"Total API quota used: {self.quota_used}")
            logger.info(f"{'='*60}")
        
        return df

    def save_raw_data(self, df: pd.DataFrame):
        """
        Save raw comments to CSV.
        
        Args:
            df: DataFrame with comments.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.raw_data_path / f"youtube_comments_{timestamp}.csv"
        
        df.to_csv(output_path, index=False)
        logger.info(f"Raw comments saved to: {output_path}")
        logger.info(f"File size: {get_size(output_path)}")
        
        # Also save as latest
        latest_path = self.raw_data_path / "youtube_comments_latest.csv"
        df.to_csv(latest_path, index=False)
        logger.info(f"Latest comments saved to: {latest_path}")
        
        return str(output_path)

    def initiate_extraction(self) -> str:
        """
        Orchestrate the complete YouTube data extraction pipeline.
        
        Returns:
            Path to saved raw comments CSV.
        """
        logger.info("=" * 60)
        logger.info("Starting YouTube Data Extraction")
        logger.info("=" * 60)
        
        try:
            # Fetch comments
            df = self.fetch_multiple_videos()
            
            if df.empty:
                logger.warning("No comments were fetched!")
                return None
            
            # Save raw data
            output_path = self.save_raw_data(df)
            
            logger.info("=" * 60)
            logger.info("YouTube Data Extraction completed successfully!")
            logger.info("=" * 60)
            
            return output_path
            
        except Exception as e:
            logger.error(f"YouTube Data Extraction failed: {e}")
            raise e


def main():
    """Run YouTube data extraction from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract YouTube comments')
    parser.add_argument('--video-id', type=str, help='Single YouTube video ID')
    parser.add_argument('--video-url', type=str, help='YouTube video URL')
    parser.add_argument('--max-comments', type=int, default=1000, help='Max comments per video')
    
    args = parser.parse_args()
    
    extractor = YouTubeDataExtractor()
    
    # Determine video IDs to process
    video_ids = []
    
    if args.video_id:
        video_ids.append(args.video_id)
    elif args.video_url:
        video_id = extractor.extract_video_id(args.video_url)
        if video_id:
            video_ids.append(video_id)
    
    # Override max comments if specified
    if args.max_comments:
        extractor.max_comments_per_video = args.max_comments
    
    # If no video specified, use config
    if not video_ids:
        video_ids = extractor.video_ids
    
    if not video_ids:
        print("Error: No video ID provided. Use --video-id, --video-url, or set video_ids in params.yaml")
        sys.exit(1)
    
    # Fetch and save
    df = extractor.fetch_multiple_videos(video_ids)
    
    if not df.empty:
        output_path = extractor.save_raw_data(df)
        print(f"\nExtraction complete! Saved to: {output_path}")
        print(f"Total comments: {len(df)}")
        print(f"Quota used: {extractor.quota_used}")
    else:
        print("\nNo comments fetched!")
        sys.exit(1)


if __name__ == "__main__":
    main()
