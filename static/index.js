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
        post = instaloader.Post.from_shortcode(L.context, url.split("/")[-2])  # Use the shortcode from the URL
        
        # Determine if the post is a video (works for Reels as well)
        if post.is_video:
            # Get the video URL (direct download link)
            media_url = post.video_url
            media_type = 'video'
        else:
            # Get the image URL (direct download link)
            media_url = post.url
            media_type = 'image'

        return {"url": media_url, "type": media_type}

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

    return jsonify(media_data)

@app.route("/download-file", methods=["GET"])
def download_file():
    media_url = request.args.get("url")
    if not media_url:
        return jsonify({"error": "Media URL is required"}), 400

    try:
        # Download the media using requests (either image or video)
        response = requests.get(media_url, stream=True)
        response.raise_for_status()

        # Get the current date and time for the filename
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")  # Format: YYYY-MM-DD_HH-MM-SS

        # Extract the file extension based on the media type
        filename = f"Downsnap-{timestamp}"
        
        # Check if it's a video or image
        if 'video' in media_url:  # If it's a video
            filename += ".mp4"
            mimetype = 'video/mp4'
        else:  # If it's an image
            filename += ".jpg"
            mimetype = 'image/jpeg'

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