AI Image Generator
A web application that generates images from text prompts using Google Cloud Vertex AI's image generation model.

🚀 Features
Generate images from text descriptions using Vertex AI

Secure image access with HMAC-signed URLs

Stores only one image per device, deleting older images

Flask-based backend with a simple web UI

🛠️ Tech Stack
Backend: Flask, Google Vertex AI

Frontend: HTML, CSS, JavaScript

Cloud Services: Google Cloud Storage, Cloud Run (optional)

🔧 Setup & Installation
1️⃣ Clone the Repository
bash
Copy
Edit
git clone https://github.com/Som94/AI-Image-Generator.git
cd AI-Image-Generator
2️⃣ Install Dependencies
bash
Copy
Edit
pip install -r requirements.txt
3️⃣ Set Up Environment Variables
Create a .env file and add:

env
Copy
Edit
CREDENTIAL_PATH_OF_GCP=<your-gcp-credentials.json>
PROJECT_ID=<your-gcp-project-id>
REGION=<your-region>
SECRET_KEY=<your-secret-key>
4️⃣ Run the Application
bash
Copy
Edit
python main.py
The app runs at: http://localhost:8080

📸 Usage
Enter a description of the image you want to generate.

Click the "Generate Image" button.

Wait for the AI to create the image.

Download the generated image.

📜 License
This project is licensed under the MIT License