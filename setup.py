from setuptools import setup, find_packages

setup(
    name="idealist",
    version="0.1.0",
    author="Yohei Nakajima",
    author_email="yohei@example.com",  # Replace with your email
    description="A flexible Python library for generating and refining creative ideas using LLMs and embeddings.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yoheinakajima/idealist",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "litellm>=0.2.0",  # Adjust version based on your project's requirements
        "pydantic>=1.8.2",
        "scikit-learn>=0.24.2",
        "numpy>=1.21.0",
        "setuptools>=57.0.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords="ideas generation creativity LLM embeddings AI",
)
