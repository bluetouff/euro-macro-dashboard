import unittest
from pathlib import Path

import plotly.graph_objects as go
from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class InteractiveAppSmokeTest(unittest.TestCase):
    def test_faq_view_runs_without_exception(self):
        app = AppTest.from_file(str(APP_PATH))
        app.query_params["view"] = "faq"

        app.run(timeout=20)

        self.assertFalse(app.exception)
        self.assertGreater(len(app.markdown), 0)

    def test_plotly_graph_objects_are_available(self):
        figure = go.Figure(go.Scatter(y=[1, 2, 3], mode="lines"))

        self.assertEqual(len(figure.data), 1)
        self.assertEqual(figure.data[0].mode, "lines")


if __name__ == "__main__":
    unittest.main()
