import json
import csv
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from litellm import completion, embedding
import logging
from sklearn.metrics.pairwise import cosine_similarity
from pydantic import BaseModel, create_model

def create_idea_models(parameters: Dict[str, Any]):
    """Dynamically create Pydantic models based on parameters."""
    field_definitions = {
        name: (str, ...) for name in parameters.keys()
    }
    Idea = create_model('Idea', **field_definitions)
    IdeaList = create_model('IdeaList', ideas=(List[Idea], ...))
    return Idea, IdeaList

class IdeaGenerator:
    """
    A flexible idea generator that uses LLMs and embeddings to create and refine ideas
    while avoiding repetition and maintaining creativity.
    """

    def __init__(self, 
                 name: str, 
                 description: str, 
                 model: str = "gpt-4o-mini",  # Specify the LLM model to use
                 embedding_model: str = "text-embedding-ada-002",  # Specify embedding model
                 anthropic_api_key: Optional[str] = None, 
                 openai_api_key: Optional[str] = None, 
                 max_recent_ideas: int = 20, 
                 debug: bool = False, 
                 generator_id: Optional[str] = None):
        """
        Initialize a new idea generator.

        Args:
            name: Name of the generator.
            description: Description of what this generator creates.
            model: LLM model to use (e.g., 'gpt-4o-mini').
            embedding_model: Embedding model to use (e.g., 'text-embedding-ada-002').
            anthropic_api_key: API key for Anthropic (optional).
            openai_api_key: API key for OpenAI (optional).
            max_recent_ideas: Maximum number of recent ideas to include in prompts.
            debug: Enable detailed debug logs.
            generator_id: Optional ID to load existing generator.
        """
        self.name = name
        self.description = description
        self.model = model
        self.embedding_model = embedding_model
        self.parameters = {}
        self.unique_field = None
        self.debug = debug
        self.generator_id = generator_id or f"{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.csv_filename = f"ideas_{self.generator_id}.csv"
        self.max_recent_ideas = max_recent_ideas

        # Set environment variables if keys are provided
        if anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key

        # Configure logging
        logging.basicConfig(level=logging.DEBUG if self.debug else logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def setup_parameters(self, parameters: Dict[str, Any]):
        """Set up the parameters that define the structure of generated ideas."""
        self.parameters = parameters
        self.unique_field = next(iter(self.parameters.keys()))
        self.Idea, self.IdeaList = create_idea_models(parameters)
        self.param_descriptions = "\n".join(f"- {name}: {desc}" for name, desc in parameters.items())
        self.csv_headers = ['id', 'timestamp'] + list(parameters.keys()) + ['embedding']

        try:
            with open(self.csv_filename, 'w', newline='') as f:
                writer = csv.writer(f)
                metadata_row = [self.name, self.description] + [''] * (len(self.csv_headers) - 2)
                writer.writerow(metadata_row)
                writer.writerow(self.csv_headers)
        except Exception as e:
            self.logger.error(f"Error initializing CSV file: {e}")
            raise

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a piece of text."""
        try:
            response = embedding(
                model=self.embedding_model,
                input=[text],
                encoding_format="float"
            )
            return response['data'][0]['embedding']
        except Exception as e:
            self.logger.error(f"Error generating embedding: {e}")
            raise

    def _generate_initial_ideas(self, recent_ideas: List[Dict], existing_values: set) -> List[Dict]:
        """Generate initial ideas using the LLM."""
        recent_ideas_text = "\n".join([
            json.dumps({k: v for k, v in idea.items() if k != 'embedding'}) for idea in recent_ideas
        ])
        messages = [
            {"role": "system", "content": f"""You are an idea generator for: {self.name}
Description: {self.description}
Generate creative and unique ideas in JSON format.
Each idea must include these fields:
{self.param_descriptions}"""},

            {"role": "user", "content": f"""Previous ideas:
{recent_ideas_text}

Generate 3 completely different ideas that are distinct from all previous ideas."""}
        ]

        try:
            response = completion(
                model=self.model,
                messages=messages,
                temperature=0.7,
                response_format=self.IdeaList
            )
            ideas = [self.Idea.parse_obj(idea).dict() for idea in json.loads(response['choices'][0]['message']['content'])["ideas"]]
            return [idea for idea in ideas if idea[self.unique_field] not in existing_values]
        except Exception as e:
            self.logger.error(f"Error generating initial ideas: {e}")
            return []

    def generate_idea(self) -> Dict:
        """Generate a new idea."""
        all_ideas, existing_values = self._load_all_ideas()
        recent_ideas = all_ideas[-self.max_recent_ideas:]
        initial_ideas = self._generate_initial_ideas(recent_ideas, existing_values)
        if not initial_ideas:
            self.logger.warning("No unique initial ideas were generated.")
            return {}

        # Refine and save the first idea
        final_idea = initial_ideas[0]
        self._save_idea(final_idea)
        return final_idea

    def _save_idea(self, idea: Dict):
        """Save an idea to the CSV file."""
        try:
            with open(self.csv_filename, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.csv_headers)
                row = {
                    'id': len(self._load_all_ideas()[0]) + 1,
                    'timestamp': datetime.now().isoformat(),
                    **idea,
                    'embedding': json.dumps(self._get_embedding(json.dumps(idea)))
                }
                writer.writerow(row)
        except Exception as e:
            self.logger.error(f"Error saving idea to CSV: {e}")
            raise
