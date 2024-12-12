# main.py
from idea_generator import IdeaGenerator
import os
import json

def create_new_generator(max_recent_ideas: int = 20):
    """Create a new birthday party ideas generator."""
    # Retrieve API keys from environment variables
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # Validate that the API keys are available
    if not anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set in the environment variables.")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set in the environment variables.")

    # Initialize the IdeaGenerator with both API keys and dynamic max_recent_ideas
    generator = IdeaGenerator(
        name="Pokemon Names",
        description="Generate unique and creative names for Pokemon characters",
        anthropic_api_key=anthropic_api_key,
        openai_api_key=openai_api_key,  # Pass the OpenAI API key here
        max_recent_ideas=max_recent_ideas,  # Set max_recent_ideas
        debug=False  # Disable debug output for minimal logging
    )

    # Setup parameters
    parameters = {
        "name": "Name of Pokemon"
    }

    generator.setup_parameters(parameters)
    return generator

def load_existing_generator(generator_id: str, max_recent_ideas: int = 20):
    """Load an existing generator by ID."""
    # Retrieve API keys from environment variables
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # Validate that the API keys are available
    if not anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set in the environment variables.")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set in the environment variables.")

    return IdeaGenerator.load(
        generator_id=generator_id,
        anthropic_api_key=anthropic_api_key,
        openai_api_key=openai_api_key,  # Pass the OpenAI API key
        max_recent_ideas=max_recent_ideas,  # Pass max_recent_ideas
        debug=False
    )

def generate_ideas(generator: IdeaGenerator, count: int = 3):
    """Generate specified number of ideas using the generator."""
    print(f"Generating {count} distinct ideas using generator: {generator.name}\n")

    for i in range(count):
        idea = generator.generate_idea()
        if not idea:
            print(f"\n\033[91mFailed to generate Idea #{i+1}.\033[0m")
            continue
        # Print only the idea name
        print(f"\033[92mIdea #{i+1}:\033[0m {idea.get('name', 'No Name')}")
        print("\n" + "="*50 + "\n")

def main():
    # Uncomment the following line to load an existing generator
    # generator = load_existing_generator("your_generator_id_here", max_recent_ideas=15)

    # Or create a new generator
    generator = create_new_generator(max_recent_ideas=15)  # Example: include last 15 ideas in prompts
    print(f"Generator ID: {generator.generator_id}\n")

    # Generate fifty distinct ideas
    generate_ideas(generator, count=50)

if __name__ == "__main__":
    main()
