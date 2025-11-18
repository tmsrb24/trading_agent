import requests
from logger import logger

class SentimentAnalyzer:
    def __init__(self):
        # Using a free API key source for demonstration. 
        # In a real application, this should be managed securely.
        self.api_url = "https://api.santiment.net/graphql"
        self.api_key_placeholder = "API_KEY_NEEDED" # Placeholder

    def get_sentiment(self, slug):
        """
        Fetches the sentiment score for a given crypto slug from Santiment.
        Handles limitations of the free plan gracefully.
        """
        if not slug or self.api_key_placeholder == "API_KEY_NEEDED":
            logger.warning("Santiment slug not provided or API key not set. Skipping sentiment analysis.")
            return 0 # Return neutral sentiment

        query = f"""
        {{
          getMetric(metric: "sentiment_balance_total") {{
            timeseriesData(
              slug: "{slug}"
              from: "utc_now-30d"
              to: "utc_now"
              interval: "1d"
            ) {{
              value
            }}
          }}
        }}
        """
        
        try:
            response = requests.post(self.api_url, json={'query': query}, headers={'Authorization': f'Apikey {self.api_key_placeholder}'})
            response.raise_for_status()
            data = response.json()

            if 'errors' in data:
                # This can happen with free plan (e.g., data not available)
                logger.warning(f"Santiment API returned an error for '{slug}': {data['errors'][0]['message']}. This may be due to free plan limitations. Proceeding without sentiment.")
                return 0 # Return neutral

            sentiment_data = data['data']['getMetric']['timeseriesData']
            if sentiment_data:
                # Return the most recent sentiment value
                return sentiment_data[-1]['value']
            else:
                logger.info(f"No sentiment data available for '{slug}'.")
                return 0 # Return neutral if no data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching sentiment data from Santiment for '{slug}': {e}")
            return 0 # Return neutral on network errors
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing sentiment data for '{slug}': {e}")
            return 0 # Return neutral on parsing errors