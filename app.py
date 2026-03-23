import os
import instaloader
import datetime
import requests
from flask import Flask, Response, render_template_string, request, jsonify, render_template, send_file, abort, send_from_directory, redirect, url_for
from io import BytesIO
from flask_talisman import Talisman 
from supabase import create_client, Client
import re
import unicodedata
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__, static_url_path='/static')

SITEMAP_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Sitemap - Downsnap</title>

<style>
/* ================= RESET ================= */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family:'Poppins',sans-serif;
    background:#0f172a;
    color:#fff;
}

/* ================= NAV ================= */
nav {
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:20px 8%;
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(10px);
}

.logo {
    color:#38bdf8;
    font-weight:bold;
    font-size:22px;
}

nav ul {
    display:flex;
    list-style:none;
    gap:20px;
}

nav a {
    color:#cbd5f5;
    text-decoration:none;
    transition:0.3s;
}

nav a:hover {
    color:#38bdf8;
}

/* ================= HEADER ================= */
.header {
    text-align:center;
    margin-top:40px;
}

.header h1 {
    font-size:38px;
    background:linear-gradient(90deg,#38bdf8,#818cf8);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}

/* ================= CONTAINER ================= */
.container {
    max-width:800px;
    margin:40px auto;
    padding:0 15px;
}

/* ================= SECTION TITLE ================= */
h2 {
    margin:25px 0 10px;
    color:#94a3b8;
}

/* ================= CARD FIX ================= */
.item {
    margin:12px 0;
}

/* 🔥 FULL CLICKABLE CARD */
.item a.link {
    display:block;
    width:100%;
    background:rgba(255,255,255,0.05);
    padding:16px;
    border-radius:12px;
    color:#38bdf8;
    text-decoration:none;
    transition:0.3s ease;
    box-shadow: 0 5px 20px rgba(0,0,0,0.2);
}

/* HOVER EFFECT */
.item a.link:hover {
    background:rgba(56,189,248,0.15);
    transform:translateY(-3px);
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
}

/* ================= FOOTER ================= */
footer {
    text-align:center;
    margin:40px 0;
    color:#64748b;
}

/* ================= RESPONSIVE ================= */
@media(max-width:600px) {
    nav {
        flex-direction:column;
        gap:10px;
    }

    .header h1 {
        font-size:28px;
    }
}
</style>

</head>

<body>

<nav>
<div class="logo">Downsnap</div>
<ul>
<li><a href="/">Home</a></li>
<li><a href="/about">About</a></li>
<li><a href="/contact">Contact</a></li>
</ul>
</nav>

<div class="header">
    <h1>Downsnap Sitemap</h1>
</div>

<div class="container">

<h2>Main Pages</h2>
{% for page in pages %}
    <div class="item">
        <a class="link" href="{{ request.host_url.rstrip('/') + url_for(page.endpoint) }}">
            {{ page.name }}
        </a>
    </div>
{% endfor %}

<h2>Blogs</h2>
{% for blog in blogs %}
    <div class="item">
        <a class="link" href="{{ request.host_url.rstrip('/') }}/blog/{{ blog['id'] }}">
            {{ blog['title'] }}
        </a>
    </div>
{% endfor %}

</div>

<footer>
© 2026 Downsnap. All rights reserved.
</footer>

</body>
</html>
"""

csp = {
    "default-src": ["'self'"],

    "script-src": [
        "'self'",
        "'unsafe-inline'",
        "'unsafe-eval'",
        "https://pagead2.googlesyndication.com",
        "https://googleads.g.doubleclick.net",
        "https://tpc.googlesyndication.com",
        "https://*.adtrafficquality.google",
        "https://www.googletagservices.com",
        "https://www.google.com",
        "https://www.gstatic.com",
        "https://cdnjs.cloudflare.com"
    ],

    "style-src": [
        "'self'",
        "'unsafe-inline'",
        "https://cdnjs.cloudflare.com"
    ],

    "img-src": [
        "'self'",
        "data:",
        "https:"
    ],

    "connect-src": [
        "'self'",
        "https://*.supabase.co",
        "https://pagead2.googlesyndication.com",
        "https://googleads.g.doubleclick.net",
        "https://*.adtrafficquality.google",
        "https://csi.gstatic.com",
        "https://www.google.com"
    ],

    "frame-src": [
        "'self'",
        "https://googleads.g.doubleclick.net",
        "https://tpc.googlesyndication.com",
        "https://*.adtrafficquality.google",
        "https://www.google.com"
    ],

    "font-src": [
        "'self'",
        "https://cdnjs.cloudflare.com",
        "https://fonts.gstatic.com"
    ]
}
Talisman(app, content_security_policy=csp)

# Apply Flask-Talisman with HSTS settings

# Supabase Configuration
SUPABASE_URL = "https://onhxdgkdgnrraaddhzkr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9uaHhkZ2tkZ25ycmFhZGRoemtyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQxNjUzNDMsImV4cCI6MjA4OTc0MTM0M30.uKlYaR1OUkuVUOKuD9LgsBzyG6jVxrIr5WffzeXqht4"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Upload folder for images
app.config['UPLOAD_FOLDER'] = "static/uploads"
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def slugify(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[-\s]+', '-', text)
    return text

# Function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Create an instance of the Instaloader class
L = instaloader.Instaloader()

@app.before_request
def enforce_https_and_www():
    url = request.url

    # If not HTTPS, redirect to HTTPS
    if not url.startswith("https://"):
        return redirect("https://" + request.host + request.full_path, code=301)

    # If not www, redirect to www
    if not request.host.startswith("www."):
        return redirect("https://www." + request.host + request.full_path, code=301)
        
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
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        image_url = None
        
        # Generate the slug from title
        slug = slugify(title)

        # Handle uploaded image
        file = request.files.get("image")
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Upload to Supabase storage
            with open(file_path, "rb") as f:
                supabase.storage.from_("blog-images").upload(filename, f)

            image_url = f"{SUPABASE_URL}/storage/v1/object/public/blog-images/{filename}"

        # Insert blog into Supabase (with slug)
        supabase.table("blogs").insert({
            "title": title,
            "content": content,
            "image_url": image_url,
            "slug": slug,  # Insert the slug
            "date_posted": datetime.datetime.utcnow().isoformat()
        }).execute()

        return redirect(url_for("blog"))

    return render_template("add_blog.html")

# Route to view all blogs
@app.route("/blog")
def blog():
    try:
        blogs = supabase.table("blogs").select("*").order("date_posted", desc=True).execute()
        return render_template("blog.html", blogs=blogs.data)
    except Exception as e:
        print("Supabase Error:", e)
        return render_template("blog.html", blogs=[])

# Route to edit a blog post
# Edit Blog Route
@app.route("/blog/edit/<slug>", methods=["GET", "POST"])
def edit_blog(slug):
    # Fetch blog using slug
    result = supabase.table("blogs").select("*").eq("slug", slug).execute()
    if not result.data:
        return "Blog not found", 404

    blog = result.data[0]

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        image_url = blog.get("image_url")

        # Generate the new slug (in case title changes)
        new_slug = slugify(title)

        file = request.files.get("image")
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Upload new image to Supabase
            with open(file_path, "rb") as f:
                supabase.storage.from_("blog-images").upload(filename, f)

            image_url = f"{SUPABASE_URL}/storage/v1/object/public/blog-images/{filename}"

        # Update Supabase
        supabase.table("blogs").update({
            "title": title,
            "content": content,
            "slug": new_slug,  # Update the slug
            "image_url": image_url
        }).eq("slug", slug).execute()

        return redirect(url_for("blog"))

    return render_template("edit_blog.html", blog=blog)

# Route to delete a blog post
@app.route("/delete_blog/<slug>", methods=["POST"])
def delete_blog(slug):
    result = supabase.table("blogs").select("*").eq("slug", slug).execute()
    if not result.data:
        return "Blog not found", 404

    blog = result.data[0]

    # Delete image from Supabase storage if exists
    if blog.get("image_url"):
        filename = blog["image_url"].split("/")[-1]
        resp = supabase.storage.from_("blog-images").remove([filename])
        if resp.get("error"):
            print("Supabase Storage Delete Error:", resp["error"])

    # Delete blog
    supabase.table("blogs").delete().eq("slug", slug).execute()
    return redirect(url_for("blog"))

@app.route('/blog/<slug>', endpoint='view_blog')
def view_blog(slug):
    # Fetch blog using slug
    result = supabase.table("blogs").select("*").eq("slug", slug).execute()
    if not result.data:
        abort(404)
    
    blog = result.data[0]
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

@app.route('/sitemap.xml', methods=['GET'])
def sitemap_xml():
    urls = []

    # Static pages
    static_pages = [
        "home", "about", "contact", "terms", "privacy", "disclaimer"
    ]
    for endpoint in static_pages:
        urls.append(request.host_url.rstrip('/') + url_for(endpoint))

    # Blogs
    try:
        response = supabase.table("blogs").select("*").execute()
        blogs_list = response.data if response.data else []
        for blog in blogs_list:
            urls.append(f"{request.host_url.rstrip('/')}/blog/{blog['id']}")
    except Exception as e:
        print("Supabase Error:", e)

    # Generate XML
    xml_sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        xml_sitemap += f'  <url><loc>{url}</loc></url>\n'
    xml_sitemap += '</urlset>'
    return Response(xml_sitemap, mimetype='application/xml')

@app.route('/sitemap')
def sitemap():
    # Static pages to include
    pages_list = [
        {"name": "Home", "endpoint": "home"},
        {"name": "About", "endpoint": "about"},
        {"name": "Contact", "endpoint": "contact"},
        {"name": "Terms", "endpoint": "terms"},
        {"name": "Privacy", "endpoint": "privacy"},
        {"name": "Disclaimer", "endpoint": "disclaimer"},
    ]

    # Load blogs from Supabase
    try:
        response = supabase.table("blogs").select("*").order("date_posted", desc=True).execute()
        blogs_list = response.data if response.data else []
    except Exception as e:
        print("Supabase Error:", e)
        blogs_list = []

    return render_template_string(SITEMAP_HTML, pages=pages_list, blogs=blogs_list, request=request)


    
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
