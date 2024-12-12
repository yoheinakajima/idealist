# Idealist

**Idealist** is a flexible Python library that leverages Large Language Models (LLMs) and embeddings to generate and refine creative ideas while avoiding repetition. It's ideal for generating unique names, themes, or any other creative content.

## Features

- **Dynamic Idea Generation**: Customize parameters to generate a wide range of ideas.
- **Uniqueness Assurance**: Ensures all generated ideas are unique and not duplicated.
- **Embedding Support**: Uses embeddings to find and avoid similar ideas.
- **Easy to Use**: Simple interface with minimal setup.

## Installation

You can install the library via pip:

~~~bash
pip install idealist
~~~

## Usage

Here's a basic example of how to use the `IdeaGenerator` class:

~~~python
from idea_generator import IdeaGenerator
import os

def main():
    # Set up environment variables for API keys
    os.environ["ANTHROPIC_API_KEY"] = "your_anthropic_api_key"
    os.environ["OPENAI_API_KEY"] = "your_openai_api_key"

    # Initialize the IdeaGenerator
    generator = IdeaGenerator(
        name="Pokemon Names",
        description="Generate unique and creative names for Pokemon characters",
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        max_recent_ideas=15,  # Number of recent ideas to include in prompts
        debug=False  # Set to True for detailed logs
    )

    # Setup parameters
    parameters = {
        "name": "Name of Pokemon"
    }

    generator.setup_parameters(parameters)

    # Generate ideas
    for i in range(5):
        idea = generator.generate_idea()
        if idea:
            print(f"Idea #{i+1}: {idea.get('name')}")
        else:
            print(f"Failed to generate Idea #{i+1}")

if __name__ == "__main__":
    main()
~~~

## API Reference

### `IdeaGenerator` Class

#### `__init__`

~~~python
IdeaGenerator(
    name: str,
    description: str,
    anthropic_api_key: str,
    openai_api_key: str,
    max_recent_ideas: int = 20,
    debug: bool = False,
    generator_id: Optional[str] = None
)
~~~

- **name**: Name of the generator.
- **description**: Description of what this generator creates.
- **anthropic_api_key**: API key for Anthropic.
- **openai_api_key**: API key for OpenAI.
- **max_recent_ideas**: Maximum number of recent ideas to include in prompts.
- **debug**: Enables detailed logging if set to `True`.
- **generator_id**: Optional ID to load an existing generator.

#### `setup_parameters`

~~~python
setup_parameters(parameters: Dict[str, Any])
~~~

- **parameters**: Dictionary defining the structure of generated ideas.

#### `generate_idea`

~~~python
generate_idea() -> Dict
~~~

- Generates a new idea based on the configured parameters.
- Returns a dictionary containing the generated idea.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

The GitHub repository for this project can be found at: [https://github.com/yoheinakajima/idealist](https://github.com/yoheinakajima/idealist)

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.