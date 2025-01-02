import instaloader
import requests
from flask import Flask, request, jsonify, render_template, send_file
from io import BytesIO
from datetime import datetime

app = Flask(__name__)

# Create an instance of the Instaloader class
L = instaloader.Instaloader()

def extract_instagram_data(url):
    try:
        # Use instaloader to get the post from the URL
        shortcode = url.split("/")[-2]
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # Initialize a list for media items
        media_items = []

        # Check if the post itself is a video or image
        if post.is_video:
            media_items.append({
                "url": post.video_url,
                "type": "video"
            })
        else:
            # Make sure the image URL is accessible
            media_items.append({
                "url": post.url,  # Using post.url for the single post image
                "type": "image"
            })
        
        # If the post contains a carousel (multiple images/videos)
        for post_media in post.get_sidecar_nodes():
            if post_media.is_video:
                media_items.append({
                    "url": post_media.video_url,  # Correctly access the video URL
                    "type": "video"
                })
            else:
                media_items.append({
                    "url": post_media.display_url,  # Correctly access the image URL
                    "type": "image"
                })

        # Log the media items for debugging
        print("Extracted media items:", media_items)

        return media_items

    except Exception as e:
        print(f"Error: {e}")
        return None

@app.route("/")
def home():
    return render_template("index.html", title="Instagram Downloader")

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get("url")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    media_data = extract_instagram_data(url)
    if not media_data:
        return jsonify({"error": "Unable to fetch media"}), 400

    return jsonify({"media": media_data})

@app.route("/download-file", methods=["GET"])
def download_file():
    media_url = request.args.get("url")
    if not media_url:
        return jsonify({"error": "Media URL is required"}), 400

    try:
        # Send a HEAD request to get the content headers without downloading the whole file
        response = requests.head(media_url, allow_redirects=True)
        response.raise_for_status()

        # Get the content type from headers
        content_type = response.headers.get('Content-Type', '').lower()

        # Get the current date and time for the filename
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")  # Format: YYYY-MM-DD_HH-MM-SS

        # Extract the file extension based on the media type
        filename = f"Downsnap-{timestamp}"
        
        # Check the content type to determine if it's a video or an image
        if 'video' in content_type:  # It's a video
            filename += ".mp4"
            mimetype = 'video/mp4'
        elif 'image' in content_type:  # It's an image
            filename += ".jpg"
            mimetype = 'image/jpeg'
        else:
            # Handle cases where content type is unknown
            return jsonify({"error": "Unsupported content type"}), 400

        # Download the media using requests (either image or video)
        response = requests.get(media_url, stream=True)
        response.raise_for_status()

        # Serve the file as an attachment
        return send_file(
            BytesIO(response.content),
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to download the file"}), 500

if __name__ == "__main__":
    app.run(debug=True)
