import base64
import hashlib
import hmac
import logging
import os
import uuid

import vertexai
from flask import Flask, abort, make_response, render_template, request, url_for
from vertexai.preview.vision_models import ImageGenerationModel

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Load environment variables
GCP_CREDENTIAL_PATH = os.getenv("CREDENTIAL_PATH_OF_GCP", "")
PROJECT_ID = os.getenv("PROJECT_ID", "")
LOCATION = os.getenv("REGION", "")

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")  # Change this in production

if GCP_CREDENTIAL_PATH:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_CREDENTIAL_PATH
else:
    logging.warning("GCP Credential path is not set.")

if not PROJECT_ID or not LOCATION:
    logging.error(
        "PROJECT_ID or LOCATION is not set. Application may not work correctly."
    )

# Initialize Flask app
app = Flask(__name__)

IMAGE_FOLDER = "static/img"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Dictionary to track which image belongs to each device
device_image_map = {}


def generate_signed_url(image_name):
    """Generate a signed URL with HMAC signature."""
    message = image_name.encode()
    signature = hmac.new(SECRET_KEY.encode(), message, hashlib.sha256).digest()
    encoded_sig = base64.urlsafe_b64encode(signature).decode()
    return url_for("fetch_img", img_name=image_name, sig=encoded_sig, _external=True)


def verify_signature(image_name, sig):
    """Verify the HMAC signature for image access."""
    expected_sig = base64.urlsafe_b64encode(
        hmac.new(SECRET_KEY.encode(), image_name.encode(), hashlib.sha256).digest()
    ).decode()
    return hmac.compare_digest(expected_sig, sig)


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html", pict_url=None)


@app.route("/generate", methods=["POST"])
def generate_image():
    try:
        prompt = request.form.get("desc", "").strip()
        if not prompt:
            abort(400, "Description cannot be empty.")

        # Extract device ID (fallback to UUID if not provided)
        device_id = request.cookies.get("device_id") or str(uuid.uuid4())

        # If the device already has a generated image, delete it
        if device_id in device_image_map:
            old_image_path = os.path.join(IMAGE_FOLDER, device_image_map[device_id])
            if os.path.exists(old_image_path):
                os.remove(old_image_path)

        # Generate a new unique file name
        new_image_name = f"{uuid.uuid4()}.png"
        new_image_path = os.path.join(IMAGE_FOLDER, new_image_name)

        # Initialize Vertex AI
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        generation_model = ImageGenerationModel.from_pretrained("imagegeneration@006")

        response = generation_model.generate_images(prompt=prompt)

        if not response.images:
            abort(500, "Failed to generate image.")

        # Save the new image
        response.images[0].save(new_image_path, include_generation_parameters=False)

        # Update the device-image mapping
        device_image_map[device_id] = new_image_name

        pict_url = generate_signed_url(new_image_name)

        # Set a cookie with device ID for future requests
        resp = make_response(render_template("index.html", pict_url=pict_url))
        resp.set_cookie("device_id", device_id, max_age=30 * 24 * 60 * 60)  # 30 days
        return resp

    except Exception as e:
        logging.error(f"Error generating image: {e}")
        abort(500, "Internal Server Error")


@app.route("/img/<img_name>", methods=["GET"])
def fetch_img(img_name):
    sig = request.args.get("sig", "")

    if not verify_signature(img_name, sig):
        abort(403, "Invalid or expired signature.")

    image_path = os.path.join(IMAGE_FOLDER, img_name)
    if not os.path.exists(image_path):
        abort(404, "Image not found.")

    with open(image_path, "rb") as f:
        img = f.read()

    response = make_response(img)
    response.headers["Content-Type"] = "image/png"
    return response


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
