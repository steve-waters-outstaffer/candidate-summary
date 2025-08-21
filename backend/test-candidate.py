import requests
import sys
import json

# --- CONFIGURATION ---
# 1. Paste your API key here
RECRUITCRM_API_KEY = "ngglqbmrYAVJwvqsDv5vI-WL-UCM1Brsk8sqpG5kMPOP4ImAmBDW1oiuFAa7kl-D7sO6PAEGEod0LmzTcgehg18xNzUwNDkyMjE0Onw6cHJvZHVjdGlvbg=="

# The base URL for the RecruitCRM API
RECRUITCRM_BASE_URL = "https://api.recruitcrm.io/v1"

def test_candidate_api(slug):
    """
    Makes a direct API call to RecruitCRM to fetch candidate data.
    """
    if not RECRUITCRM_API_KEY or "PASTE_YOUR" in RECRUITCRM_API_KEY:
        print("!!! ERROR: Please paste your API key into the RECRUITCRM_API_KEY variable in this script.")
        return

    # Construct the full URL for the API endpoint
    url = f"{RECRUITCRM_BASE_URL}/candidates/{slug}"

    # Set up the required headers for authorization
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {RECRUITCRM_API_KEY}"
    }

    print(f"--- Making GET request to: {url} ---")

    try:
        # Make the GET request to the API
        response = requests.get(url, headers=headers)

        # Print the HTTP status code from the response
        print(f"\nResponse Status Code: {response.status_code}")

        # Check if the request was successful
        if response.status_code == 200:
            print("\n✅ Success! API Response:")
            # Pretty-print the JSON response
            print(json.dumps(response.json(), indent=2))
        else:
            print("\n❌ Error! API returned a non-200 status code.")
            print("Server Response:")
            # Print the error details from the server
            print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"\n❌ A network error occurred: {e}")

if __name__ == "__main__":
    # Check if a command-line argument (the slug) was provided
    if len(sys.argv) > 1:
        candidate_slug = sys.argv[1]
        test_candidate_api(candidate_slug)
    else:
        print("Usage: python test_candidate.py <candidate_slug>")
        print("Example: python test_candidate.py 17556812678390100119JVC")

