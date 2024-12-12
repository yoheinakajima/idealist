# idea_generator/generator.py

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
    # Create field definitions for the Idea model
    field_definitions = {
        name: (str, ...) for name in parameters.keys()  # ... means required field
    }

    # Create the Idea model dynamically
    Idea = create_model('Idea', **field_definitions)

    # Create the IdeaList model dynamically
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
                 anthropic_api_key: str, 
                 openai_api_key: str,  # Added OpenAI API key
                 max_recent_ideas: int = 20,  # New parameter for maximum recent ideas
                 debug: bool = False, 
                 generator_id: Optional[str] = None):
        """
        Initialize a new idea generator or load an existing one.

        Args:
            name: Name of the generator
            description: Description of what this generator creates
            anthropic_api_key: API key for Anthropic
            openai_api_key: API key for OpenAI
            max_recent_ideas: Maximum number of recent ideas to include in prompts
            debug: Whether to print debug information
            generator_id: Optional ID to load existing generator
        """
        self.name = name
        self.description = description
        self.parameters = {}
        self.unique_field = None  # To be set in setup_parameters
        self.debug = debug
        self.generator_id = generator_id or f"{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.csv_filename = f"ideas_{self.generator_id}.csv"
        self.max_recent_ideas = max_recent_ideas  # Store the max_recent_ideas
        os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key
        os.environ["OPENAI_API_KEY"] = openai_api_key  # Set OpenAI API key

        # Configure logging
        logging.basicConfig(level=logging.DEBUG if self.debug else logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    @classmethod
    def load(cls, generator_id: str, anthropic_api_key: str, openai_api_key: str, 
             max_recent_ideas: int = 20, debug: bool = False) -> 'IdeaGenerator':
        """Load an existing generator by ID."""
        csv_filename = f"ideas_{generator_id}.csv"
        if not os.path.exists(csv_filename):
            raise ValueError(f"No generator found with ID: {generator_id}")

        with open(csv_filename, 'r') as f:
            metadata = next(f).strip().split(',')
            name = metadata[0]
            description = metadata[1]

        return cls(name=name, 
                  description=description, 
                  anthropic_api_key=anthropic_api_key, 
                  openai_api_key=openai_api_key,  # Pass OpenAI API key
                  max_recent_ideas=max_recent_ideas,  # Pass max_recent_ideas
                  debug=debug, 
                  generator_id=generator_id)

    def setup_parameters(self, parameters: Dict[str, Any]):
        """Set up the parameters that define the structure of generated ideas."""
        self.parameters = parameters
        self.unique_field = next(iter(self.parameters.keys()))  # Assuming first key is unique

        # Create dynamic Pydantic models
        self.Idea, self.IdeaList = create_idea_models(parameters)

        # Create parameter descriptions for prompts
        self.param_descriptions = "\n".join(f"- {name}: {desc}" for name, desc in parameters.items())

        # Set up all columns we want to track
        self.csv_headers = ['id', 'timestamp'] + list(parameters.keys()) + ['embedding']

        if self.debug:
            self.logger.debug("=== CSV Setup ===")
            self.logger.debug(f"Headers: {self.csv_headers}")
            self.logger.debug(f"Parameters: {parameters}")

        # Initialize CSV with headers and metadata
        try:
            with open(self.csv_filename, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write metadata row - pad with empty strings to match column count
                metadata_row = [self.name, self.description] + [''] * (len(self.csv_headers) - 2)
                writer.writerow(metadata_row)
                # Write headers
                writer.writerow(self.csv_headers)
        except Exception as e:
            self.logger.error(f"Error initializing CSV file: {e}")
            raise

    def _load_all_ideas(self) -> Tuple[List[Dict], set]:
        """Load all ideas from storage and return a list of ideas and a set of unique field values."""
        if not os.path.exists(self.csv_filename):
            return [], set()

        ideas = []
        unique_values = set()
        try:
            with open(self.csv_filename, 'r') as f:
                # Skip metadata row
                next(f)
                # Read with proper headers
                reader = csv.DictReader(f, fieldnames=self.csv_headers)
                # Skip header row
                next(f)

                for row in reader:
                    # Include both parameter fields and embedding
                    idea = {
                        **{k: row[k] for k in self.parameters.keys()},
                        'embedding': row['embedding']
                    }
                    ideas.append(idea)
                    value = idea.get(self.unique_field)
                    if value:
                        unique_values.add(value)
        except Exception as e:
            self.logger.error(f"Error loading ideas from CSV: {e}")
            raise

        if self.debug:
            self.logger.debug("=== Loading All Ideas ===")
            self.logger.debug(f"Total ideas loaded: {len(ideas)}")
            if ideas:
                # Show truncated version of the last idea for debug
                sample = {k: v[:100] + '...' if k == 'embedding' and len(str(v)) > 100 else v 
                         for k, v in ideas[-1].items()}
                self.logger.debug(f"Sample idea: {sample}")

        return ideas, unique_values

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a piece of text using OpenAI's text-embedding-ada-002 via LiteLLM."""
        try:
            response = embedding(
                model="text-embedding-ada-002",
                input=[text],
                encoding_format="float"  # Ensure embeddings are returned as floats
            )
            # Extract the embedding from the response
            embedding_result = response['data'][0]['embedding']
            return embedding_result
        except Exception as e:
            self.logger.error(f"Error generating embedding: {e}")
            raise

    def _generate_initial_ideas(self, all_ideas: List[Dict], existing_values: set) -> List[Dict]:
        """Generate initial set of ideas using the LLM."""
        # Limit to the most recent N ideas based on max_recent_ideas
        recent_ideas = all_ideas[-self.max_recent_ideas:] if len(all_ideas) > self.max_recent_ideas else all_ideas
        recent_ideas_text = "\n".join([
            json.dumps({k: v for k, v in idea.items() if k != 'embedding'}) for idea in recent_ideas
        ])

        messages = [
            {"role": "system", "content": f"""You are an idea generator for: {self.name}
Description: {self.description}
Generate creative and unique ideas in JSON format.
Always return a JSON object with an 'ideas' array containing exactly 3 ideas.
Each idea must include these fields:
{self.param_descriptions}

IMPORTANT: Each idea must be completely unique and different from all previously generated ideas.
Do not repeat any {self.unique_field} that has been used before."""},
            {"role": "user", "content": f"""Previous ideas already used:
{recent_ideas_text}

Generate 3 completely different high-level ideas that are distinct from all previous ideas.
Return them in this exact format:
{{
    "ideas": [
        {{
            {', '.join(f'"{k}": "value for {k}"' for k in self.parameters.keys())}
        }},
        ... (2 more ideas)
    ]
}}"""}
        ]

        try:
            response = completion(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,  # Adjusted temperature for balance between creativity and coherence
                response_format=self.IdeaList
            )

            # Parse the response and ensure uniqueness
            content = response['choices'][0]['message']['content']
            content_json = json.loads(content)
            ideas = [self.Idea.parse_obj(idea).dict() for idea in content_json["ideas"]]

            # Filter out any duplicates
            unique_ideas = []
            for idea in ideas:
                value = idea.get(self.unique_field)
                if value and value not in existing_values:
                    unique_ideas.append(idea)
                    existing_values.add(value)

            return unique_ideas
        except Exception as e:
            self.logger.error(f"Error generating initial ideas: {e}")
            raise

    def _find_similar_ideas(self, idea: Dict, all_ideas: List[Dict], num_similar: int) -> List[Dict]:
        """Find similar ideas using embedding similarity."""
        if not all_ideas:
            return []

        idea_text = json.dumps(idea)
        try:
            idea_embedding = self._get_embedding(idea_text)
        except Exception as e:
            self.logger.error(f"Error retrieving embedding for idea: {e}")
            return []

        # Track seen ideas to avoid duplicates
        seen_ideas = set()
        similarities = []

        for stored_idea in all_ideas:
            # Create a hashable representation of the idea
            idea_key = json.dumps(stored_idea, sort_keys=True)
            if idea_key in seen_ideas:
                continue

            try:
                stored_embedding = json.loads(stored_idea['embedding'])
                similarity = cosine_similarity([idea_embedding], [stored_embedding])[0][0]
                similarities.append((float(similarity), stored_idea))
                seen_ideas.add(idea_key)
            except Exception as e:
                self.logger.error(f"Error computing similarity: {e}")
                continue

        # Sort by similarity score (first element of tuple)
        similarities.sort(key=lambda x: x[0], reverse=True)

        # Return only the ideas (second element of tuple)
        return [idea for _, idea in similarities[:num_similar]]

    def _refine_idea(self, candidate_ideas: List[Dict], similar_ideas: List[Dict], all_ideas: List[Dict]) -> Dict:
        """Refine and select the final idea."""
        # Minimal logging: only log errors if debug is enabled
        if self.debug:
            self.logger.debug("=== Debug Information ===")
            self.logger.debug("Recent Ideas:")
            for i, idea in enumerate(all_ideas, 1):
                first_field = self.unique_field
                self.logger.debug(f"{i}. {idea.get(first_field, 'No value')}")

            self.logger.debug("\nNew Candidate Ideas:")
            for i, idea in enumerate(candidate_ideas, 1):
                first_field = self.unique_field
                self.logger.debug(f"{i}. {idea.get(first_field, 'No value')}")

            self.logger.debug("\nSimilar Ideas Found:")
            for i, idea in enumerate(similar_ideas, 1):
                first_field = self.unique_field
                self.logger.debug(f"{i}. {idea.get(first_field, 'No value')}")
            self.logger.debug("======================")

        # Construct a string of all ideas without embeddings
        all_ideas_text = "\n".join([
            "RECENT IDEAS:",
            *[json.dumps({k: v for k, v in idea.items() if k != 'embedding'}) for idea in all_ideas],
            "\nSIMILAR IDEAS:",
            *[json.dumps({k: v for k, v in idea.items() if k != 'embedding'}) for idea in similar_ideas],
            "\nCANDIDATE IDEAS:",
            *[json.dumps(idea) for idea in candidate_ideas]
        ])

        messages = [
            {"role": "system", "content": f"""You are an idea generator for: {self.name}
Description: {self.description}
Select and refine ideas in JSON format.
Return a single idea with these fields:
{self.param_descriptions}"""},
            {"role": "user", "content": f"""Given these ideas:
{all_ideas_text}

Select and refine ONE of the candidate ideas to be distinct from all recent and similar ideas.
Return it in this exact format:
{{
    {', '.join(f'"{k}": "value for {k}"' for k in self.parameters.keys())}
}}"""}
        ]

        try:
            response = completion(
                model="gpt-4o-mini",  # Default to gpt-4o-mini
                messages=messages,
                temperature=0.7,
                response_format=self.Idea
            )

            content = response['choices'][0]['message']['content']
            content_json = json.loads(content)
            return self.Idea.parse_obj(content_json).dict()
        except Exception as e:
            self.logger.error(f"Error refining idea: {e}")
            raise

    def generate_idea(self) -> Dict:
        """Generate a new idea using the configured parameters."""
        # Load all existing ideas and unique values
        all_ideas, existing_values = self._load_all_ideas()

        # Generate initial ideas ensuring uniqueness across all ideas
        try:
            initial_ideas = self._generate_initial_ideas(all_ideas, existing_values)
        except Exception as e:
            self.logger.error(f"Error generating initial ideas: {e}")
            return {}

        if not initial_ideas:
            self.logger.warning("No unique initial ideas were generated.")
            return {}

        # Find similar ideas for each initial idea
        all_similar_ideas = []
        for idea in initial_ideas:
            try:
                similar_ideas = self._find_similar_ideas(idea, all_ideas, 10)
                all_similar_ideas.extend(similar_ideas)
            except Exception as e:
                self.logger.error(f"Error finding similar ideas: {e}")
                continue

        # Refine and select final idea
        try:
            final_idea = self._refine_idea(initial_ideas, all_similar_ideas, all_ideas)
        except Exception as e:
            self.logger.error(f"Error refining final idea: {e}")
            return {}

        if not final_idea:
            self.logger.warning("No final idea was refined.")
            return {}

        # Generate embedding for final idea
        idea_text = json.dumps(final_idea)
        try:
            embedding_result = self._get_embedding(idea_text)
        except Exception as e:
            self.logger.error(f"Error generating embedding for final idea: {e}")
            return {}

        # Prepare row as a dictionary
        row = {
            'id': len(all_ideas) + 1,
            'timestamp': datetime.now().isoformat(),
        }
        # Add all parameter values
        for key in self.parameters.keys():
            row[key] = str(final_idea.get(key, ''))  # Ensure string values
        # Add embedding
        row['embedding'] = json.dumps(embedding_result)

        if self.debug:
            self.logger.debug("=== CSV Row ===")
            self.logger.debug(f"Headers: {self.csv_headers}")
            order = [f"{i}. {h}" for i, h in enumerate(self.csv_headers)]
            self.logger.debug(f"Column order: {order}")
            self.logger.debug(f"Row data: { {k: (v[:100] + '...' if isinstance(v, str) and len(v) > 100 else v) for k, v in row.items()} }")

        # Save to CSV
        try:
            with open(self.csv_filename, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.csv_headers)
                writer.writerow(row)
        except Exception as e:
            self.logger.error(f"Error saving idea to CSV: {e}")
            raise

        return final_idea
