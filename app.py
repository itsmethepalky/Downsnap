import os
import instaloader
import datetime
import requests
from flask import Flask, request, jsonify, render_template, send_file, abort, send_from_directory, redirect, url_for
from io import BytesIO
from flask_talisman import Talisman 
from supabase import create_client, Client
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__, static_url_path='/static')



# Apply Flask-Talisman with HSTS settings

# Supabase Configuration
SUPABASE_URL = "https://blhepmcjpzyrmoowqswk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJsaGVwbWNqcHp5cm1vb3dxc3drIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyMTY4MjAsImV4cCI6MjA1Nzc5MjgyMH0.GIM_xTqed1R1Dmgpmp85fZr_cs2m2FDw4488nmKHCLs"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Upload folder for images
app.config['UPLOAD_FOLDER'] = "static/uploads"
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

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

        return media_items

    except Exception as e:
        print(f"Error: {e}")
        return None

@app.route("/")
def home():
    return render_template("index.html", title="Downsnap", content_title="Check out Downsnap")

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
        now = datetime.datetime.now()
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

# Blog routes
@app.route("/add_blog", methods=["GET", "POST"])
def add_blog():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        image_url = None

        if "image" in request.files:
            file = request.files["image"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                # Upload image to Supabase Storage
                with open(file_path, "rb") as f:
                    response = supabase.storage.from_("blog-images").upload(filename, f)
                
                # Generate public URL for the image
                image_url = f"{SUPABASE_URL}/storage/v1/object/public/blog-images/{filename}"

        # Insert blog into Supabase
        data = {
            "title": title,
            "content": content,
            "image_url": image_url,
            "date_posted": datetime.datetime.utcnow().isoformat()
        }
        supabase.table("blogs").insert(data).execute()

        return redirect(url_for("blog"))

    return render_template("add_blog.html")

# Route to view all blogs
@app.route("/blog")
def blog():
    blogs = supabase.table("blogs").select("*").order("date_posted", desc=True).execute()
    return render_template("blog.html", blogs=blogs.data)

# Route to edit a blog post
@app.route("/edit_blog/<int:id>", methods=["GET", "POST"])
def edit_blog(id):
    blog = supabase.table("blogs").select("*").eq("id", id).execute().data[0]

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        image_url = blog["image_url"]

        if "image" in request.files:
            file = request.files["image"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                # Upload new image to Supabase Storage
                with open(file_path, "rb") as f:
                    response = supabase.storage.from_("blog-images").upload(filename, f)

                # Generate new public URL
                image_url = f"{SUPABASE_URL}/storage/v1/object/public/blog-images/{filename}"

        # Update blog in Supabase
        supabase.table("blogs").update({"title": title, "content": content, "image_url": image_url}).eq("id", id).execute()
        return redirect(url_for("blog"))

    return render_template("edit_blog.html", blog=blog)

# Route to delete a blog post
@app.route("/delete_blog/<int:id>", methods=["POST"])
def delete_blog(id):
    blog = supabase.table("blogs").select("image_url").eq("id", id).execute().data[0]

    # Delete image from Supabase Storage
    if blog["image_url"]:
        filename = blog["image_url"].split("/")[-1]
        supabase.storage.from_("blog-images").remove(filename)

    # Delete blog post
    supabase.table("blogs").delete().eq("id", id).execute()
    return redirect(url_for("blog"))

@app.route('/blog/<int:blog_id>')
def view_blog(blog_id):
    blog = supabase.table("blogs").select("*").eq("id", blog_id).execute().data[0]
    
    if not blog:
        abort(404)

    return render_template('view_blog.html', blog=blog)

# Additional static routes for SEO, contact, terms, etc.
@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')

@app.route('/about')
def about():
    return render_template('about.html')
    
@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')

@app.route('/robots.txt')
def robots():
    return send_from_directory(app.template_folder, 'robots.txt')

@app.route('/ads.txt')
def serve_ads_txt():
    return send_from_directory(app.template_folder, 'ads.txt')

@app.route('/sitemap.xml')
def sitemap_xml():
    return render_template('sitemap.xml'), 200, {'Content-Type': 'application/xml'}
    
@app.route('/sitemap')
def sitemap():
    return send_from_directory(app.root_path, 'sitemap.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.root_path, 'favicon.ico')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/amp')
def amp_page():
    return render_template('amp_index.html')

@app.route('/logo.png')
def logo():
    return send_from_directory(app.root_path, 'logo.png')

if __name__ == "__main__":
    app.run(debug=True)