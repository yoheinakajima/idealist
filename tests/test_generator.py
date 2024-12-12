import unittest
import os
from idea_generator import IdeaGenerator

class TestIdeaGenerator(unittest.TestCase):

    def setUp(self):
        # Set up environment variables for testing (optional)
        os.environ["OPENAI_API_KEY"] = "test_openai_api_key"

        # Initialize IdeaGenerator with test parameters
        self.generator = IdeaGenerator(
            name="Test Generator",
            description="Test Description",
            model="gpt-4o-mini",
            embedding_model="text-embedding-ada-002",
            openai_api_key="test_openai_api_key",
            max_recent_ideas=5,
            debug=True
        )

        # Setup test parameters
        parameters = {
            "name": "Name of Idea"
        }
        self.generator.setup_parameters(parameters)

    def test_generate_idea(self):
        # Generate an idea
        idea = self.generator.generate_idea()

        # Check if the idea has the required field
        self.assertIn("name", idea)
        self.assertIsInstance(idea["name"], str)
        self.assertNotEqual(idea["name"], "")

    def tearDown(self):
        # Remove the test CSV file after tests
        if os.path.exists(self.generator.csv_filename):
            os.remove(self.generator.csv_filename)

if __name__ == '__main__':
    unittest.main()
