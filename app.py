import instaloader
import requests
from flask import Flask, request, jsonify, render_template, send_file, send_from_directory, redirect
from io import BytesIO
from datetime import datetime


app = Flask(__name__,
static_url_path='/static')



# Get the secret key from the environment variable
# Create an instance of the Instaloader class
L = instaloader.Instaloader()
@app.before_request
def redirect_to_non_www():
    if request.host == 'www.downsnap.onrender.com':  # WWW
        return redirect("https://downsnap.onrender.com" + request.full_path, code=301)


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
    content_url = "https://downsnap.onrender.com/"
    content_description = "Download and share videos easily using Downsnap."

    return render_template("index.html", title="Downsnap",
    content_title="Check ou Downsnap",
    url=content_url,  description=content_description)

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

# Route to serve the sw.js file for service worker verification
@app.route('/sw.js')
def serve_sw():
    """Serve the service worker file."""
    return send_from_directory('', 'sw.js', mimetype='application/javascript')


# Contact Us route

    
@app.route('/story-downloader')
def story_downloader():
    return render_template('index.html')

@app.route('/reels-downloader')
def reels_downloader():
    return render_template('index.html')



@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')
@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')
    
@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')
@app.route('/robots.txt')
def robots():
    return send_from_directory(app.template_folder, 'robots.txt')
@app.route('/ads.txt')
def serve_ads_txt():
  return send_from_directory(app.template_folder, 'ads.txt')
  

# Serve sitemap.xml from the templates folder
@app.route('/sitemap.xml')
def sitemap_xml():
    return render_template('sitemap.xml'), 200, {'Content-Type': 'application/xml'}

# Serve sitemap.html from the root folder
@app.route('/sitemap')
def sitemap():
    return send_from_directory(app.root_path, 'sitemap.html')
    
@app.route('/favicon')
def favicon():
    return send_from_directory(app.root_path, 'favicon.ico')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
@app.route('/amp')

def amp_page():
    return render_template('amp_index.html')  # This is your AMP version
  
@app.route('/logo.png')
def logo():
    return send_from_directory(app.root_path, 'logo.png')
    

    

if __name__ == "__main__":
    app.run(debug=True)