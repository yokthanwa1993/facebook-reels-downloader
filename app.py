import sys
import subprocess
import os
import requests
import uuid
from flask import Flask, request, jsonify, render_template, send_from_directory, after_this_request
from urllib.parse import quote, urlsplit
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Create 'templates' and 'downloads' directories if they don't exist
if not os.path.exists('templates'):
    os.makedirs('templates')
if not os.path.exists('downloads'):
    os.makedirs('downloads')

app = Flask(__name__)
DOWNLOAD_FOLDER = 'downloads'
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER


def download_reel(url, output_path="."):
    """
    Downloads a Facebook Reel using yt-dlp and returns the final filename.
    Checks for errors and file existence. Uses cookies if available.
    """
    cookie_filepath = None
    facebook_cookie = os.getenv("FACEBOOK_COOKIE")

    # Create a temporary cookie file if the cookie variable is set
    if facebook_cookie:
        cookie_filename = f"cookie_{uuid.uuid4()}.txt"
        cookie_filepath = os.path.join(output_path, cookie_filename)
        with open(cookie_filepath, "w") as f:
            f.write(facebook_cookie)
        app.logger.info("Using temporary cookie file for download.")

    try:
        # Template for the output filename
        output_template = f"{output_path}/%(title)s.%(ext)s"

        # First, get the expected filename from yt-dlp without downloading
        get_filename_command = [
            sys.executable, "-m", "yt_dlp",
            "--get-filename",
            "-o", output_template,
            url
        ]

        filename_result = subprocess.run(
            get_filename_command,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        # The full path to the expected file
        full_path = filename_result.stdout.strip().splitlines()[-1]

        # Now, execute the actual download
        # We force a universally compatible format (H.264/AAC) to prevent codec issues.
        download_command = [
            sys.executable, "-m", "yt_dlp",
            # This format string prefers compatible codecs, avoiding re-encoding if possible.
            # It looks for the best video with an AVC (H.264) codec and the best audio with
            # an AAC codec, merges them into an mp4. Falls back to other best options if not found.
            "-f", "bestvideo[vcodec^=avc]+bestaudio[acodec^=mp4a]/best[ext=mp4]/best",
            "-o", output_template,
            url
        ]

        # Add cookie argument if a cookie file was created
        if cookie_filepath:
            download_command.extend(["--cookies", cookie_filepath])

        # We don't use --print here, we check for file existence
        subprocess.run(
            download_command,
            check=True,  # This will raise CalledProcessError on yt-dlp errors
            capture_output=True,  # Capture output to prevent it from cluttering the server log
            text=True,
            encoding='utf-8'
        )

        # CRITICAL: Verify the file was actually created
        if not os.path.exists(full_path):
            raise FileNotFoundError(
                f"yt-dlp reported success, but output file is missing: {full_path}")

        # We only need the filename part for the download link
        filename = os.path.basename(full_path)
        return filename, None

    except subprocess.CalledProcessError as e:
        # Log the actual error from yt-dlp for easier debugging
        stderr_output = e.stderr.strip().lower()

        # Check for specific error patterns that indicate a private/login-required video
        if "login" in stderr_output or "unsupported url" in stderr_output:
            error_message = "Could not download. The video may be private or requires a login to view."
        else:
            error_message = f"yt-dlp failed. Please check the URL and try again."

        print(f"yt-dlp error details: {e.stderr.strip()}")
        return None, error_message
    except FileNotFoundError as e:
        # Handle cases where the file isn't created
        error_message = str(e)
        print(error_message)
        return None, error_message
    except Exception as e:
        error_message = f"An unexpected server error occurred: {e}"
        print(error_message)
        return None, error_message

    finally:
        # CRITICAL: Always try to delete the temporary cookie file
        if cookie_filepath and os.path.exists(cookie_filepath):
            try:
                os.remove(cookie_filepath)
                app.logger.info("Successfully deleted temporary cookie file.")
            except Exception as e:
                app.logger.error(
                    f"Error deleting temporary cookie file {cookie_filepath}: {e}")


def resolve_share_url(url):
    """
    Resolves a Facebook share link (/share/r/...) to its final, clean reel URL.
    Returns the original URL if it's not a share link or fails to resolve.
    """
    if "/share/r/" in url:
        try:
            # Send a HEAD request to get the redirect location without downloading the body
            response = requests.head(url, allow_redirects=True, timeout=5)
            final_url = response.url
            # Clean the URL by removing query parameters
            cleaned_url = urlsplit(final_url)._replace(query=None).geturl()
            app.logger.info(f"Resolved {url} -> {cleaned_url}")
            return cleaned_url
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Could not resolve share URL {url}: {e}")
            return url  # Fallback to original URL on error
    return url


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/download')
def api_download():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"success": False, "error": "URL parameter is missing."}), 400

    # Resolve the URL before passing it to the downloader
    resolved_url = resolve_share_url(video_url)

    filename, error = download_reel(
        resolved_url, app.config['DOWNLOAD_FOLDER'])

    if error:
        return jsonify({"success": False, "error": error}), 500

    filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)

    @after_this_request
    def cleanup(response):
        """
        Delete the file after the response has been sent.
        """
        try:
            os.remove(filepath)
            app.logger.info(f"Successfully deleted {filepath}")
        except Exception as e:
            app.logger.error(f"Error deleting file {filepath}: {e}")
        return response

    # Send the downloaded file directly as the response
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)


# This route is no longer needed by the frontend, but can be kept for direct access
@app.route('/downloads/<path:filename>')
def downloaded_file(filename):
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
