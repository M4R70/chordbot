# Ultimate Guitar Scraper
import requests
from bs4 import BeautifulSoup
import json
import re
import urllib.parse
import os # Import os to check environment variables

# --- PythonAnywhere Proxy Setup ---
# Check if running on PythonAnywhere and set up proxy if needed
PA_PROXY = None
if 'PYTHONANYWHERE_SITE' in os.environ:
    print("Detected PythonAnywhere environment. Configuring proxy.")
    proxy_url = 'http://proxy.server:3128'
    PA_PROXY = {
        "http": proxy_url,
        "https": proxy_url,
    }

# --- Helper function for requests ---
def make_request(url, **kwargs):
    """Wrapper for requests.get that adds proxy if running on PythonAnywhere."""
    if PA_PROXY:
        kwargs['proxies'] = PA_PROXY
        # Might need to disable SSL verification if proxy causes issues, but try without first
        # kwargs['verify'] = False
    print(f"Making request to: {url} with proxy: {PA_PROXY is not None}")
    return requests.get(url, **kwargs)


# --- LaCuerda Scraper ---

def _scrape_lacuerda(query: str) -> str | None:
    """
    Internal function to scrape LaCuerda.net.

    Args:
        query: The song title and artist.

    Returns:
        Formatted chords and lyrics as a string if found, otherwise None.
    """
    print(f"Trying LaCuerda.net for: {query}")
    # LaCuerda search usually works better if we split artist/song, but let's try combined first
    # A more robust approach might involve trying to parse artist/song from the query
    search_term = urllib.parse.quote(query)
    search_url = f"https://lacuerda.net/BUSCADOR/index.php?keyword={search_term}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    try:
        # Use the helper function
        search_response = make_request(search_url, headers=headers, timeout=10)
        search_response.raise_for_status()
        search_soup = BeautifulSoup(search_response.text, 'html.parser')

        # Find the results table
        results_table = search_soup.find('table', {'class': 'tbl'})
        if not results_table:
            print("LaCuerda: No results table found.")
            return None

        # Find the first link within the results table (simplistic approach)
        first_result_link = results_table.find('a', href=re.compile(r'/tabs/'))
        if not first_result_link or not first_result_link.get('href'):
            print("LaCuerda: No valid result link found in table.")
            return None

        song_rel_url = first_result_link['href']
        # Ensure the URL is absolute
        song_url = urllib.parse.urljoin("https://lacuerda.net/", song_rel_url)
        print(f"LaCuerda: Found potential match: {song_url}")

        # Fetch the song page using the helper function
        song_response = make_request(song_url, headers=headers, timeout=10)
        song_response.raise_for_status()
        # LaCuerda often uses ISO-8859-1 encoding
        song_response.encoding = 'ISO-8859-1'
        song_soup = BeautifulSoup(song_response.text, 'html.parser')

        # Find the <pre> tag containing the chords/lyrics
        pre_tag = song_soup.find('pre', id='tab_content')
        if not pre_tag:
            print("LaCuerda: Could not find <pre id='tab_content'> tag.")
            return None

        # Extract text content
        # Replace <br> tags with newlines if necessary (BeautifulSoup often handles this)
        content = pre_tag.get_text(separator='\n').strip()

        # Basic formatting (remove potential ad lines, etc. - might need refinement)
        lines = content.splitlines()
        cleaned_lines = [line for line in lines if not line.strip().startswith(('lacuerda.net', 'ATENCION:', '-------'))]
        formatted_content = "\n".join(cleaned_lines)

        return formatted_content

    except requests.exceptions.Timeout:
        print("LaCuerda: Request timed out.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"LaCuerda: Network error: {e}")
        return None
    except Exception as e:
        print(f"LaCuerda: An unexpected error occurred: {e}")
        return None

# --- Cifra Club Scraper ---

def _scrape_cifraclub(query: str) -> str | None:
    """
    Internal function to scrape CifraClub.com.

    Args:
        query: The song title and artist.

    Returns:
        Formatted chords and lyrics as a string if found, otherwise None.
    """
    print(f"Trying CifraClub.com for: {query}")
    # Cifra Club search needs the query formatted for the URL
    search_term = urllib.parse.quote(query)
    # Note: Cifra Club search might redirect. requests handles redirects by default.
    search_url = f"https://www.cifraclub.com/find/?q={search_term}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    try:
        # --- 1. Search ---
        # Cifra Club's search might directly land on the song page if it's a good match,
        # or show a search results page. We need to handle both.
        # Use the helper function
        search_response = make_request(search_url, headers=headers, timeout=15, allow_redirects=True)
        search_response.raise_for_status()
        search_soup = BeautifulSoup(search_response.text, 'html.parser')

        # Check if we landed directly on a song page (look for the <pre> tag)
        pre_tag = search_soup.find('pre')
        song_url = search_response.url # The final URL after redirects

        if pre_tag:
             print(f"CifraClub: Directly landed on song page: {song_url}")
             song_soup = search_soup # Use the current soup
        else:
            # --- If not direct, parse search results ---
            print("CifraClub: Parsing search results page...")
            # Find the first result link (this might need refinement based on actual page structure)
            # Look for links within an ordered list <ol class="list-links">
            results_list = search_soup.find('ol', class_='list-links')
            first_result_link = None
            if results_list:
                first_result_link = results_list.find('a', href=True)

            if not first_result_link:
                print("CifraClub: No valid result link found on search page.")
                return None

            song_rel_url = first_result_link['href']
            # Ensure the URL is absolute (relative to cifraclub.com)
            song_url = urllib.parse.urljoin("https://www.cifraclub.com/", song_rel_url)
            print(f"CifraClub: Found potential match link: {song_url}")

            # --- 2. Fetch the song page ---
            # Use the helper function
            song_response = make_request(song_url, headers=headers, timeout=10)
            song_response.raise_for_status()
            # Cifra Club usually uses UTF-8, but let requests handle encoding detection
            song_soup = BeautifulSoup(song_response.text, 'html.parser')
            pre_tag = song_soup.find('pre') # Find the pre tag again

        if not pre_tag:
            print("CifraClub: Could not find <pre> tag on song page.")
            return None

        # --- 3. Extract and Format ---
        # Replace <b> tags around chords with nothing
        for b_tag in pre_tag.find_all('b'):
            b_tag.replace_with(b_tag.text)

        # Get text content, preserving line breaks
        content = pre_tag.get_text(separator='\n').strip()

        # Basic formatting (remove potential ad lines, etc. - might need refinement)
        lines = content.splitlines()
        # Example filter: remove lines that are just chord diagrams or ads
        cleaned_lines = [line for line in lines if not re.match(r'^\s*(\|--.*--\||Tom:|Intro:|Base:|Solo:)', line.strip())]
        formatted_content = "\n".join(cleaned_lines).strip()

        # Check if content is substantial (sometimes empty <pre> tags exist)
        if len(formatted_content) < 20:
             print("CifraClub: Extracted content seems too short or empty.")
             return None

        return formatted_content

    except requests.exceptions.Timeout:
        print("CifraClub: Request timed out.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"CifraClub: Network error: {e}")
        return None
    except Exception as e:
        print(f"CifraClub: An unexpected error occurred: {e}")
        return None


# --- Combined Scraper ---

def get_song_chords(query: str) -> str:
    """
    Searches Ultimate Guitar, falling back to LaCuerda.net, then CifraClub.com,
    and returns the formatted lyrics and chords.

    Args:
        query: The song title and artist (e.g., "Wonderwall Oasis").

    Returns:
        A multiline string containing the formatted chords and lyrics,
        or an error message if the song is not found on any site or scraping fails.
    """
    print(f"--- Searching Ultimate Guitar for: {query} ---")
    last_error = None # Store the last significant error
    search_url = f"https://www.ultimate-guitar.com/search.php?search_type=title&value={urllib.parse.quote(query)}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    try:
        # --- 1. Search for the song ---
        # Use the helper function
        search_response = make_request(search_url, headers=headers, timeout=15) # Added timeout
        search_response.raise_for_status() # Raise an exception for bad status codes

        search_soup = BeautifulSoup(search_response.text, 'html.parser')

        # --- Find and parse the embedded JSON data ---
        # UG often embeds data in a <script> tag. Let's find it.
        script_tag = search_soup.find('div', {'class': 'js-store'})

        if not script_tag or not script_tag.get('data-content'):
             # Fallback: Try finding script tag directly (less reliable)
             script_tag_direct = search_soup.find('script', string=re.compile(r'window\.UGAPP\.store\.page'))
             if script_tag_direct:
                 json_text_match = re.search(r'window\.UGAPP\.store\.page\s*=\s*(\{.*?\});', script_tag_direct.string, re.DOTALL)
                 if json_text_match:
                     try:
                         data = json.loads(json_text_match.group(1))
                     except json.JSONDecodeError:
                         return "Failed to parse JSON data from script tag."
                 else:
                     return "Could not extract JSON data pattern from script tag."
             else:
                return "Could not find the js-store div or relevant script tag for search results."
        else:
             # Preferred method: Parse from data-content attribute
             try:
                 data = json.loads(script_tag['data-content'])
             except json.JSONDecodeError:
                 return "Failed to parse JSON data from js-store data-content."


        # Navigate through the JSON structure to find results
        # The exact path might change, adjust based on inspection if needed
        results = data.get('store', {}).get('page', {}).get('data', {}).get('results', [])
        if not results:
            last_error = f"UG: No results found for '{query}'."
            print(last_error)
            # Don't return yet, try fallbacks

        # Find the first 'Chords' type result
        song_url = None
        for result in results:
            if result.get('type') == 'Chords':
                song_url = result.get('tab_url')
                if song_url:
                    print(f"Found Chords tab: {song_url}")
                    break

        if not song_url:
            last_error = f"UG: No 'Chords' tab found for '{query}'."
            print(last_error)
            # Don't return yet, try fallbacks

        # --- 2. Fetch the song page ---
        print(f"Fetching song page: {song_url}")
        # Use the helper function
        song_response = make_request(song_url, headers=headers, timeout=15) # Added timeout
        song_response.raise_for_status()

        song_soup = BeautifulSoup(song_response.text, 'html.parser')

        # --- Find and parse the embedded JSON data for the tab ---
        tab_script_div = song_soup.find('div', {'class': 'js-store'})

        if not tab_script_div or not tab_script_div.get('data-content'):
            # Fallback: Try finding script tag directly (less reliable)
            tab_script_tag_direct = song_soup.find('script', string=re.compile(r'window\.UGAPP\.store\.page'))
            if tab_script_tag_direct:
                tab_json_match = re.search(r'window\.UGAPP\.store\.page\s*=\s*(\{.*?\});', tab_script_tag_direct.string, re.DOTALL)
                if tab_json_match:
                    try:
                        tab_data = json.loads(tab_json_match.group(1))
                    except json.JSONDecodeError:
                        return "Failed to parse tab JSON data from script tag."
                else:
                    return "Could not extract tab JSON data pattern from script tag."
            else:
                return "Could not find the js-store div or relevant script tag for tab content."
        else:
            # Preferred method: Parse from data-content attribute
            try:
                tab_data = json.loads(tab_script_div['data-content'])
            except json.JSONDecodeError:
                return "Failed to parse tab JSON data from js-store data-content."


        # Navigate to the tab content - path might need adjustment
        tab_content_data = tab_data.get('store', {}).get('page', {}).get('data', {})
        if not tab_content_data:
             return "Could not find 'data' object in tab JSON."

        # Try finding content in different possible locations within the JSON
        tab_content = tab_content_data.get('tab_view', {}).get('wiki_tab', {}).get('content', '')
        if not tab_content:
             # Alternative path observed sometimes
             tab_content = tab_content_data.get('tab', {}).get('text', '') # Check if content is directly in 'text'

        # Yet another possible structure
        if not tab_content and 'tab_view' in tab_content_data and 'content' in tab_content_data['tab_view']:
             tab_content = tab_content_data['tab_view']['content']

        if not tab_content:
            last_error = "UG: Could not extract tab content (lyrics and chords)."
            print(last_error)
            # Don't return yet, try fallbacks

        # If we have UG content, format and return it
        if tab_content:
            # --- 3. Format the output ---
            # The content often uses [ch]ChordName[/ch] tags. Replace them.
            formatted_content = re.sub(r'\[ch\](.*?)\[/ch\]', r'\1', tab_content)
            # Remove other tags like [tab]...[/tab] if necessary (optional)
            formatted_content = re.sub(r'\[/?tab\]', '', formatted_content)
            # Remove [Verse], [Chorus] etc. tags for cleaner output (optional)
            # formatted_content = re.sub(r'\[/?(Verse|Chorus|Intro|Outro|Bridge|Instrumental)\]\s*', '', formatted_content)
            print("UG: Success!")
            return formatted_content.strip()

    except requests.exceptions.RequestException as e:
        last_error = f"UG: Network error: {e}"
        print(last_error)
    except json.JSONDecodeError as e:
        last_error = f"UG: Error parsing JSON data: {e}"
        print(last_error)
    except Exception as e:
        last_error = f"UG: An unexpected error occurred: {e}"
        print(last_error)

    # --- Fallback 1: LaCuerda ---
    print("\n--- Trying LaCuerda.net as fallback ---")
    lacuerda_result = _scrape_lacuerda(query)
    if lacuerda_result:
        print("LaCuerda: Success!")
        return lacuerda_result
    else:
        print("LaCuerda: Failed.")
        # Keep the last_error from UG if LaCuerda also failed

    # --- Fallback 2: Cifra Club ---
    print("\n--- Trying CifraClub.com as fallback ---")
    cifraclub_result = _scrape_cifraclub(query)
    if cifraclub_result:
        print("CifraClub: Success!")
        return cifraclub_result
    else:
        print("CifraClub: Failed.")
        # If all failed, return the last significant error or a generic message
        return last_error if last_error else f"Could not find '{query}' on Ultimate Guitar, LaCuerda.net, or CifraClub.com."


# --- Example Usage ---
if __name__ == "__main__":
    # Example found on UG
    song_query_ug = "Wonderwall Oasis"
    print(f"\n>>> Testing Query: {song_query_ug}")
    chords_and_lyrics_ug = get_song_chords(song_query_ug)
    print("\n--- Chords and Lyrics ---")
    print(chords_and_lyrics_ug)
    print("-------------------------\n")

    # Example likely found on LaCuerda (Spanish song) - UG might find it too now
    song_query_lc = "De Musica Ligera Soda Stereo"
    print(f"\n>>> Testing Query: {song_query_lc}")
    chords_and_lyrics_lc = get_song_chords(song_query_lc)
    print("\n--- Chords and Lyrics ---")
    print(chords_and_lyrics_lc)
    print("-------------------------\n")

    # Example likely found on CifraClub (Brazilian song)
    song_query_cc = "Garota de Ipanema Tom Jobim"
    print(f"\n>>> Testing Query: {song_query_cc}")
    chords_and_lyrics_cc = get_song_chords(song_query_cc)
    print("\n--- Chords and Lyrics ---")
    print(chords_and_lyrics_cc)
    print("-------------------------\n")

    # Example likely not found on any
    song_query_none = "NonExistentSong BlahBlahArtistXYZ"
    print(f"\n>>> Testing Query: {song_query_none}")
    chords_and_lyrics_none = get_song_chords(song_query_none)
    print("\n--- Chords and Lyrics ---")
    print(chords_and_lyrics_none)
