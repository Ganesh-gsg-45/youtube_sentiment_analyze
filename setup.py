from setuptools import setup, find_packages

setup(
    name="sentiment-scope",
    version="1.0.0",
    author="Ganesh",
    description="YouTube Sentiment Analysis Pipeline",
    packages=find_packages(),
    install_requires=[
        "nltk==3.9.1",
        "joblib==1.4.2",
        "scikit-learn==1.5.1",
    ],
    python_requires=">=3.9",
)

