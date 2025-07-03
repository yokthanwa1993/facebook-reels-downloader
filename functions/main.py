# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

import functions_framework
from urllib.parse import quote, urlsplit
from flask import Flask, request, jsonify, send_file, after_this_request
import tempfile
import uuid
import requests
import os
import subprocess
import sys
from firebase_functions import https_fn
from firebase_functions.options import set_global_options
from firebase_admin import initialize_app

# For cost control, you can set the maximum number of containers that can be
# running at the same time. This helps mitigate the impact of unexpected
# traffic spikes by instead downgrading performance. This limit is a per-function
# limit. You can override the limit for each function using the max_instances
# parameter in the decorator, e.g. @https_fn.on_request(max_instances=5).
set_global_options(max_instances=10)

initialize_app()

# This is the Flask app instance
server = Flask(__name__)


def download_reel(url, output_path=None):
    """
    Downloads a Facebook Reel using yt-dlp and returns the path to the downloaded file.
    """
    if output_path is None:
        # Use a temporary directory for downloads
        output_path = tempfile.mkdtemp()

    cookie_filepath = None
    facebook_cookie = os.getenv("FACEBOOK_COOKIE")

    if facebook_cookie:
        cookie_filename = f"cookie_{uuid.uuid4()}.txt"
        cookie_filepath = os.path.join(output_path, cookie_filename)
        with open(cookie_filepath, "w") as f:
            f.write(facebook_cookie)

    try:
        # Find the yt-dlp executable in the venv's bin directory for robustness
        yt_dlp_executable = os.path.join(
            os.path.dirname(sys.executable), 'yt-dlp')
        if not os.path.isfile(yt_dlp_executable):
            # Fallback if the script is not found directly
            yt_dlp_executable = 'yt-dlp'

        output_template = f"{output_path}/%(title)s.%(ext)s"

        get_filename_command = [
            yt_dlp_executable,
            "--get-filename", "-o", output_template, url
        ]
        filename_result = subprocess.run(
            get_filename_command,
            check=True, capture_output=True, text=True, encoding='utf-8'
        )
        full_path = filename_result.stdout.strip().splitlines()[-1]

        download_command = [
            yt_dlp_executable,
            "-f", "bestvideo[vcodec^=avc]+bestaudio[acodec^=mp4a]/best[ext=mp4]/best",
            "-o", output_template, url
        ]

        if cookie_filepath:
            download_command.extend(["--cookies", cookie_filepath])

        subprocess.run(
            download_command,
            check=True, capture_output=True, text=True, encoding='utf-8'
        )

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Output file is missing: {full_path}")

        return full_path, None

    except subprocess.CalledProcessError as e:
        stderr_output = e.stderr.strip().lower()
        if "login" in stderr_output or "unsupported url" in stderr_output:
            error_message = "Could not download. The video may be private or requires a login."
        else:
            error_message = "yt-dlp failed. Please check the URL and try again."
        print(f"yt-dlp error: {e.stderr.strip()}")
        return None, error_message
    except Exception as e:
        error_message = f"An unexpected server error occurred: {e}"
        print(error_message)
        return None, error_message
    finally:
        if cookie_filepath and os.path.exists(cookie_filepath):
            try:
                os.remove(cookie_filepath)
            except Exception as e:
                print(f"Error deleting cookie file {cookie_filepath}: {e}")


def resolve_share_url(url):
    """
    Resolves Facebook share links to their final reel URL.
    """
    if "/share/r/" in url:
        try:
            response = requests.head(url, allow_redirects=True, timeout=5)
            cleaned_url = urlsplit(response.url)._replace(query=None).geturl()
            print(f"Resolved {url} -> {cleaned_url}")
            return cleaned_url
        except requests.exceptions.RequestException as e:
            print(f"Could not resolve share URL {url}: {e}")
            return url
    return url


@server.route('/', defaults={'path': ''})
@server.route('/<path:path>')
def catch_all(path):
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"success": False, "error": "URL parameter is missing."}), 400

    resolved_url = resolve_share_url(video_url)
    filepath, error = download_reel(resolved_url)

    if error:
        return jsonify({"success": False, "error": error}), 500

    @after_this_request
    def cleanup(response):
        """Delete the file after the response has been sent."""
        try:
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
                dir_path = os.path.dirname(filepath)
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
        except Exception as e:
            print(f"Error during cleanup: {e}")
        return response

    return send_file(filepath, as_attachment=True)


@https_fn.on_request()
def app(req: https_fn.Request) -> https_fn.Response:
    with server.request_context(req.environ):
        return server.full_dispatch_request()
