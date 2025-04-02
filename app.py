from flask import Flask, render_template, request
from markupsafe import Markup # Import Markup from markupsafe
import ug_scraper # Import the scraper module

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Handles both displaying the form (GET) and processing the query (POST).
    """
    query = ""
    result_html = "" # Use Markup to render HTML safely
    error = ""

    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if query:
            try:
                print(f"Received query: {query}")
                # Call the scraper function from the imported module
                chords_result = ug_scraper.get_song_chords(query)
                print(f"Scraper returned: {chords_result[:100]}...") # Log snippet

                # Basic formatting for HTML display (preserve line breaks)
                # Replace newlines with <br> tags
                formatted_result = chords_result.replace('\n', '<br>')
                result_html = Markup(f"<pre>{formatted_result}</pre>") # Wrap in <pre> for formatting

            except Exception as e:
                print(f"Error during scraping or processing: {e}")
                error = f"An unexpected error occurred: {e}"
        else:
            error = "Please enter a song title and artist."

    # Render the template, passing the query, result, and error message
    return render_template('index.html', query=query, result_html=result_html, error=error)

# The following block is typically not used when deploying with Gunicorn on Render
# if __name__ == '__main__':
#     app.run(debug=False) # Ensure debug is False for production-like environments
