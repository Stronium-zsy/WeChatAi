
import logging
import jsonpickle
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class EmoBERTaClient:
    def __init__(self, url_emoberta="http://127.0.0.1:10006/"):
        self.url_emoberta = url_emoberta

    def run_text(self, text: str) -> dict:
        """Send data to the flask server.

        Args
        ----
        text: raw text

        Returns
        -------
        dict: response from the server.
        """
        data = {"text": text}

        logging.debug("sending text to server...")
        data = jsonpickle.encode(data)
        response = requests.post(self.url_emoberta, json=data)
        logging.info(f"got {response} from server!...")
        response.raise_for_status()  # Raise an error for bad status codes
        response_data = jsonpickle.decode(response.text)

        logging.info(f"emoberta results: {response_data}")
        return response_data


