# Facebook Reels Downloader

A simple application to download Facebook Reels videos via a web interface.

This project consists of:
- A Python Flask backend that provides an API to download videos.
- A simple HTML frontend to interact with the API.
- It uses `yt-dlp` to handle the downloading process.

## Prerequisites

- Python 3.6+
- `pip` for installing packages

## Installation

1.  **Clone or download the project files.**
    Ensure you have `app.py` and `requirements.txt` in your project directory.

2.  **Install dependencies:**
    Open your terminal or command prompt, navigate to the project directory, and run the following command to install the necessary Python libraries:
    ```bash
    pip install -r requirements.txt
    ```

## How to Run the Web Application

1.  **Start the Flask server:**
    In your terminal, run the following command:
    ```bash
    python app.py
    ```

2.  **Open the web interface:**
    Open your web browser and go to the following address:
    [http://127.0.0.1:5001](http://127.0.0.1:5001)

## How to Use

1.  Once the web page is open, you will see an input field.
2.  Paste the URL of the Facebook Reel you want to download into the field.
3.  Click the "Download" button.
4.  Wait for the download to complete. A status message will be displayed.
5.  Once successful, a download link for the video will appear. Click on it to save the video to your computer.

All downloaded videos are saved in the `downloads` directory on the server. 