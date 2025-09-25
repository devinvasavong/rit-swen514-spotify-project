import os, base64, requests, json
from flask import Flask, request, jsonify
from urllib.parse import urlparse
from flask_cors import CORS

# To be set in environment variables for security later
CLIENT_ID=""
CLIENT_SECRET=""

app = Flask(__name__)
CORS(app,
     resources={r"/analyze": {"origins": "*"}}
)

def get_token():
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    r = requests.post("https://accounts.spotify.com/api/token",
                      headers={"Authorization": f"Basic {auth}"},
                      data={"grant_type":"client_credentials"}, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]

def fetch_playlist_tracks(token, playlist_id):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?limit=100"
    headers = {"Authorization": f"Bearer {token}"}
    items = []
    while url:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        js = r.json()
        items += js.get("items", [])
        url = js.get("next")
    return items

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json() or {}
    pid = data.get("playlist_id")
    if not pid:
        return jsonify({"error":"missing playlist_id"}), 400

    if not isinstance(pid, str) or len(pid) < 10 or len(pid) > 100:
        return jsonify({"error":"invalid playlist_id"}), 400

    try:
        token = get_token()
        items = fetch_playlist_tracks(token, pid)
        out = []
        for it in items:
            t = it.get("track")
            if not t: continue
            out.append({
                "id": t.get("id"),
                "name": t.get("name"),
                "artists": [a['name'] for a in t.get("artists",[])],
                "album": t.get("album", {}).get("name"),
                "duration_ms": t.get("duration_ms"),
                "preview_url": t.get("preview_url")
            })
        return jsonify({"count": len(out), "tracks": out})
    except requests.HTTPError as e:
        return jsonify({"error":"spotify api error", "details": str(e)}), 502
    except Exception as e:
        return jsonify({"error":"internal error", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)