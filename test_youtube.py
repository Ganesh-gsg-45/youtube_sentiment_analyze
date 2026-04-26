"""Quick test script for YouTube sentiment analysis."""
import sys
import io

# Force UTF-8 output on Windows to handle emojis/special chars in YouTube comments
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, '.')

from app import analyze_youtube_video

# Test with Rick Astley - Never Gonna Give You Up (the video in params.yaml)
url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

print(f'Testing YouTube analysis...')
print(f'URL: {url}')
print('=' * 60)

try:
    result = analyze_youtube_video(url, max_comments=50)

    if result.get('error'):
        print(f'API Error: {result["error"]}')
        sys.exit(1)

    print(f'Video Title    : {result.get("video_title", "N/A")}')
    print(f'Channel        : {result.get("channel", "N/A")}')
    print(f'Views          : {result.get("view_count", 0):,}')
    print(f'Total Comments : {result.get("comment_count", 0):,}')
    print(f'Comments Fetched: {result.get("total_comments_fetched", 0)}')

    print()
    print('SENTIMENT DISTRIBUTION:')
    print('-' * 40)
    dist = result.get('sentiment_distribution', {})
    for sentiment, data in dist.items():
        bar = '#' * int(data.get('percentage', 0) // 2)
        print(f'  {sentiment:10s}: {data["count"]:3d} ({data["percentage"]:5.1f}%)  [{bar:<25}]')

    print()
    print('TOP POSITIVE COMMENTS:')
    print('-' * 40)
    for c in result.get('top_positive_comments', [])[:3]:
        print(f'  Confidence: {c["confidence"]:.2%}')
        print(f'  Text: {c["text"][:100]}')
        print()

    print('TOP NEGATIVE COMMENTS:')
    print('-' * 40)
    for c in result.get('top_negative_comments', [])[:3]:
        print(f'  Confidence: {c["confidence"]:.2%}')
        print(f'  Text: {c["text"][:100]}')
        print()

    print('=' * 60)
    print('YouTube analysis completed successfully!')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
